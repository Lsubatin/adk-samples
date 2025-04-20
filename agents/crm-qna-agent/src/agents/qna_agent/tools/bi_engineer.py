# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""BI Engineer Agent"""

import hashlib
import io
import json
import jsonschema
import os
import time

from google.adk.tools import ToolContext

from google.genai.types import GenerateContentConfig, Part, SafetySetting

from google.cloud.exceptions import BadRequest, NotFound
from google.cloud.bigquery import Client, QueryJobConfig

import altair as alt
import pandas as pd

from .utils import get_genai_client
from tools.chart_evaluator import evaluate_chart

MAX_RESULT_ROWS_DISPLAY = 50
BI_ENGINEER_AGENT_MODEL_ID = "gemini-2.5-pro-preview-03-25" # "gemini-1.5-pro-002"  "gemini-2.0-flash-001"
BI_ENGINEER_FIX_AGENT_MODEL_ID = "gemini-2.5-pro-preview-03-25" # "gemini-2.0-flash-001"

_bq_project_id = os.environ.get("BQ_PROJECT_ID", os.environ.get("GOOGLE_CLOUD_PROJECT", None))
if _bq_project_id == "":
    _bq_project_id = None
_data_project_id = os.environ.get("SFDC_BQ_PROJECT_ID", "kittycorn-public")
_location = os.environ.get("BQ_LOCATION", "US")
_dataset = os.environ.get("BQ_DATASET", "sfdc__raw__6_3__us")

def _clean_vega(chart_json: str) -> str:
    if "```vega-lite" in chart_json:
        vega = chart_json.split("```vega-lite", 1)[-1].rsplit("```", 1)[0]
    elif "```vega" in chart_json:
        vega = chart_json.split("```vega", 1)[-1].rsplit("```", 1)[0]
    elif "```json" in chart_json:
        vega = chart_json.split("```json", 1)[-1].rsplit("```", 1)[0]
    else:
        vega = chart_json
    return vega

def _create_chat(model: str, history: list):
    return get_genai_client().chats.create(model=model,
                                               config=GenerateContentConfig(
                                                    system_instruction="You are an experienced Business Intelligence engineer, proficient in building business charts and dashboards.",
                                                    temperature=0.0,
                                                    top_p=0.0,
                                                    safety_settings=[
                                                    SafetySetting(
                                                        category="HARM_CATEGORY_DANGEROUS_CONTENT", # type: ignore
                                                        threshold="BLOCK_NONE", # "BLOCK_ONLY_HIGH", # type: ignore
                                                    ),
                                                ]),
                                                history=history)

def bi_engineer_tool(original_business_question: str,
                           question_that_sql_result_can_answer: str,
                           sql_code: str,
                           tool_context: ToolContext) -> str:
    """Senior BI Engineer. Executes SQL code.

    Args:
        original_business_question (str): Original business question.
        question_that_sql_result_can_answer (str): Specific question or sub-question that SQL result can answer.
        sql_code (str): BigQuery SQL code execute.

    Returns:
        str: Chart image id and the result of executing the SQL code in CSV format.
    """
    client = Client(project=_bq_project_id, location=_location)
    try:
        dataset_location = client.get_dataset(
                                f"{_data_project_id}.{_dataset}").location
        job_config = QueryJobConfig(use_query_cache=False)
        df: pd.DataFrame = client.query(sql_code,
                     job_config=job_config,
                     location=dataset_location).result().to_dataframe()
    except (BadRequest, NotFound) as ex:
        err_text = ex.args[0].strip()
        return f"BIGQUERY ERROR: {err_text}"

    chart_prompt = f"""
You are an experienced Business Intelligence engineer tasked with creating a data visualization.

**Context:**
1.  **Original Business Question:** ```{original_business_question}```
2.  **Specific Question Answered by Data:** ```{question_that_sql_result_can_answer}```
3.  **SQL Query Used:**
    ```sql
    {sql_code}
    ```
4.  **Resulting Data Preview (first {min(10,len(df))} rows):**
    ```
    {df.head(10)}
    ```
5.  **Total Rows in Result:** `{len(df)}`

**Your Task:**
Generate a single, complete Vega-Lite **4** JSON specification for a chart that effectively visualizes the provided data to answer the `{question_that_sql_result_can_answer}`.

**Key Requirements & Best Practices:**

1.  **Chart Type Selection:**
    *   Choose the most appropriate chart type (e.g., bar, line, area, pie, scatter, text) based on the data structure (column types, number of rows: `{len(df)}`) and the question being answered.
    *   Number of data rows is `{len(df)}`. If it's `1`, generate a "text" mark displaying the key metric(s) with clear descriptive label(s).

2.  **Data Encoding:**
    *   **Use Provided Data:** Map columns directly from the provided data (`Resulting Data Preview` above shows available column names).
    *   **Prioritize Readability:** Use descriptive entity names (e.g., `CustomerName`) for axes, legends, and tooltips instead of identifiers (e.g., `CustomerID`) whenever available. Look for columns ending in `Name`, `Label`, `Category`, etc.
    *   **Correct Data Types:** Accurately map data columns to Vega-Lite types (`quantitative`, `temporal`, `nominal`, `ordinal`).
    *   **Axes & Legends:**
        *   Use clear, concise axis titles and legend titles.
        *   Ensure legends accurately represent the encoding (e.g., color, shape) and include units (e.g., "$", "%", "Count") if applicable and known.
        *   Format axes appropriately (e.g., date formats, currency formats).

3.  **Data Transformation & Refinement:**
    *   **Sorting:** Apply meaningful sorting (e.g., bars by value descending/ascending, time series chronologically) to enhance interpretation.
    *   **Filtering:** Consider adding a `transform` filter *only if* it clarifies the visualization by removing irrelevant data (e.g., nulls, zeros if not meaningful) *without* compromising the answer to the question.
    *   **Top-K:** If dealing with high cardinality dimensions, consider using a chart type and grouping that would make the chart easy to understand.

4.  **Chart Aesthetics & Formatting:**
    *   **Title:** Provide a clear, descriptive title for the chart that summarizes its main insight or content relevant to the question.
    *   **Readability:** Ensure all labels (axes, data points, legends) are easily readable and do not overlap. Rotate or reposition labels if necessary. Use tooltips to show details on hover.
    *   **Dashboard-Ready:** Design the chart to be clear and effective when viewed as part of a larger dashboard. Aim for simplicity and avoid clutter.
    *   **Sizing and Scaling:**
        - Define reasonable `width` and `height` suitable for a typical dashboard component. *Minimal* width is 1152. *Minimal* height is 648.
        - The chart must be comfortable to view using 16 inch screen at resolution PPI=72.
        - Consider using `autosize: fit` properties if appropriate.
        - Avoid making the chart excessively large or small.
        - If using `vconcat` or `hconcat`, adjust width and height accordingly to accommodate all series.

5.  **Strict Technical Constraints:**
    *   **Vega-Lite Version:** MUST use Vega-Lite **version 4** schema.
    *   **Valid Syntax:** Ensure the generated JSON is syntactically correct and adheres strictly to the Vega-Lite 4 specification. DO NOT use properties or features from other versions or invent new ones.
    *   **Output Format:** Your entire output MUST be **only** the raw Vega-Lite JSON code. Do NOT include markdown formatting (like ```json ... ```), comments, explanations, or any other text outside the JSON structure.

**Final Check:** Before outputting, mentally review if the generated chart directly addresses the `{question_that_sql_result_can_answer}` using the provided data and adheres to all the requirements above.

**OUTPUT Vega-Lite 4 JSON:**
"""
    vega_fix_chat = None
    vega_chat = _create_chat(BI_ENGINEER_AGENT_MODEL_ID, [])
    chart_json_results = vega_chat.send_message(chart_prompt)
    chart_json = chart_json_results.text or ""

    if not chart_json:
        return "ERROR: Could not generate a chart."

    for _ in range(3): # 3 tries to make a good chart
        while True:
            try:
                chart_json = _clean_vega(chart_json) # type: ignore
                vega_dict = json.loads(chart_json)
                vega_dict["data"] = {}
                vega_dict["data"]["values"] = []
                vega_dict.pop("datasets", None)
                vega_chart = alt.Chart.from_dict(vega_dict)
                with io.BytesIO() as tmp:
                    vega_chart.save(tmp, "png")
                break
            except (jsonschema.ValidationError, json.JSONDecodeError, ValueError, ReferenceError) as ex:
                message = f"ERROR {type(ex).__name__}: " + ex.message if ex is jsonschema.ValidationError else str(ex)
                if not vega_fix_chat:
                    vega_fix_chat = _create_chat(BI_ENGINEER_AGENT_MODEL_ID, vega_chat.get_history())
                chart_json = vega_fix_chat.send_message(message).text
        # rows_dicts = df.to_dict("records")
        # vega_dict["data"]["values"] = rows_dicts
        error_reason = ""
        try:
            vega_chart = alt.Chart.from_dict(vega_dict)
            vega_chart_json = json.dumps(vega_dict, indent=1)
            vega_chart.data = df
        except ValueError as ex:
            error_reason = str(ex)

        if not error_reason:
            with io.BytesIO() as file:
                vega_chart.save(file, "png")
                file.seek(0)
                png_data = file.getvalue()
                evaluate_chart_result = evaluate_chart(png_data, question_that_sql_result_can_answer, len(df), tool_context)
            if not evaluate_chart_result or evaluate_chart_result.is_good:
                break
            error_reason = evaluate_chart_result.reason
        if not error_reason:
            break

        chart_json = vega_chat.send_message(f"""Fix the chart based on the feedback.
                                            Only output Vega 4 Lite json.

            ***Feedback on the chart below**
            {error_reason}


            ***CHART**

            ``json
            {vega_chart_json}
            ````
            """).text

    data_file_name = f"{tool_context.invocation_id}.parquet"
    parquet_bytes = df.to_parquet()
    tool_context.save_artifact(filename=data_file_name,
                               artifact=Part.from_bytes(
                                   data=parquet_bytes,
                                   mime_type="application/parquet"))
    file_name = f"{tool_context.invocation_id}.vg"
    tool_context.save_artifact(filename=file_name, artifact=Part.from_text(
            text=vega_chart_json))

    # tool_context.save_artifact(
    #                 filename=f"{time.time_ns()}.md",
    #                 artifact=Part.from_text(
    #                                 text=df.to_markdown(index=False)
    #                 )
    # )
    with io.BytesIO() as file:
        vega_chart.save(file, "png", ppi=72)
        file.seek(0)
        data = file.getvalue()
        new_image_name = f"{tool_context.invocation_id}.png" # hashlib.md5(data).hexdigest()
        tool_context.save_artifact(filename=new_image_name,
                                artifact=Part.from_bytes(
                                    mime_type="image/png",
                                    data=data
                                ))
        tool_context.state["chart_image_name"] = new_image_name

    csv = df.head(MAX_RESULT_ROWS_DISPLAY).to_csv(index=False)
    if len(df) > MAX_RESULT_ROWS_DISPLAY:
        csv_message = f"**FIRST {MAX_RESULT_ROWS_DISPLAY} ROWS OF DATA**:"
    else:
        csv_message = "**DATA**:"

    return f"chart_image_id: `{new_image_name}`\n\n{csv_message}\n\n```csv\n{csv}\n```\n"
