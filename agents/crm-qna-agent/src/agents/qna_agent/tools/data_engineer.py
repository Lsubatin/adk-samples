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
"""Data Engineer Agent"""

import json
import os
from pathlib import Path
from typing import Tuple

from pydantic import BaseModel

from google.genai.types import Content, GenerateContentConfig, Part, SafetySetting
from google.cloud.exceptions import BadRequest, NotFound
from google.cloud.bigquery import Client, QueryJobConfig

from .utils import get_genai_client


DATA_ENGINEER_AGENT_MODEL_ID = "gemini-2.5-pro-preview-03-25"
SQL_VALIDATOR_MODEL_ID =  "gemini-2.0-flash-001"
_DatedConversionRate_name = "DatedConversionRate"
_DEFAULT_KITTYCORN_MAPPING="Account=accounts,Case=cases,Contact=contacts,DatedConversionRate=dated_conversion_rates,Event=events,Lead=leads,Opportunity=opportunities,RecordType=record_types,Task=tasks,User=users"
_DEFAULT_METADATA_FILE="sfdc_metadata.json"

_bq_project_id = os.environ.get("BQ_PROJECT_ID", os.environ.get("GOOGLE_CLOUD_PROJECT", None))
if _bq_project_id == "":
    _bq_project_id = None
_data_project_id = os.environ.get("SFDC_BQ_PROJECT_ID", "kittycorn-public")
_location = os.environ.get("BQ_LOCATION", "US")
_dataset = os.environ.get("BQ_DATASET", "sfdc__raw__6_3__us")
_sfdc_metadata_path = os.environ.get("SFDC_METADATA_FILE", _DEFAULT_METADATA_FILE)
if not Path(_sfdc_metadata_path).exists():
    if "/" not in _sfdc_metadata_path:
        _sfdc_metadata_path = str(Path(__file__).parent.parent / _sfdc_metadata_path)

_sfdc_metadata = Path(_sfdc_metadata_path).read_text(encoding="utf-8")
_sfdc_metadata_dict = json.loads(_sfdc_metadata)

# Account for kittycorn-based demo data that uses different table names
if _data_project_id == "kittycorn-public":
    mapping = os.environ.get("SFDC_TABLE_NAME_MAPPING",
                             _DEFAULT_KITTYCORN_MAPPING)
    for m in mapping.split(","):
        k, v = m.split("=")
        if k in _sfdc_metadata_dict:
            if k == "DatedConversionRate":
                _DatedConversionRate_name = v
            _sfdc_metadata_dict[v] = _sfdc_metadata_dict[k]
            _sfdc_metadata_dict.pop(k)

# Only keep metadata for tables that exist in the dataset.
_final_dict = {}
client = Client(_bq_project_id, location=_location)
for table in client.list_tables(f"{_data_project_id}.{_dataset}"):
    if table.table_id in _sfdc_metadata_dict:
        table_dict = _sfdc_metadata_dict[table.table_id]
        _final_dict[table.table_id] = table_dict
        table_obj = client.get_table(f"{_data_project_id}.{_dataset}.{table.table_id}")
        for f in table_obj.schema:
            if f.name in table_dict["columns"]:
                table_dict["columns"][f.name]["field_type"] = f.field_type

_sfdc_metadata = json.dumps(_final_dict, indent=2)
_sfdc_metadata_dict = _final_dict

def _clean_sql(sql: str) -> str:
    if "```sql" in sql:
        sql = sql.split("```sql", 1)[-1].rsplit("```", 1)[0]
    elif "```" in sql:
        sql = sql.split("```", 1)[-1].rsplit("```", 1)[0]

    if "```sql" in sql:
        return _clean_sql(sql)

    return sql

class SQLResult(BaseModel):
    sql_code: str
    error: str = ""

def sql_validator(sql_code: str) -> Tuple[str, str]:
    """SQL Validator. Validates BigQuery SQL query using BigQuery client.
    Returns "SUCCESS" if the query is valid, error text otherwise.

    Args:
        sql_code (str): BigQuery SQL code to validate.

    Returns:
        str: "SUCCESS" if SQL is valid, error text otherwise.
        str: modified SQL code.
    """
    print("Running SQL validator.")
    sql_code_to_run = sql_code
    for k,v in _sfdc_metadata_dict.items():
        sfdc_name = v["salesforce_name"]
        full_name = f"`{_data_project_id}.{_dataset}.{sfdc_name}`"
        sql_code_to_run = sql_code_to_run.replace(
            full_name,
            f"`{_data_project_id}.{_dataset}.{k}`"
        )

    client = Client(project=_bq_project_id, location=_location)
    try:
        dataset_location = client.get_dataset(
                                f"{_data_project_id}.{_dataset}").location
        job_config = QueryJobConfig(dry_run=True, use_query_cache=False)
        client.query(sql_code,
                     job_config=job_config,
                     location=dataset_location).result()
    except (BadRequest, NotFound) as ex:
        err_text = ex.args[0].strip()
        return f"ERROR: {err_text}", sql_code_to_run
    return "SUCCESS", sql_code_to_run


def data_engineer(request: str) -> SQLResult:
    """
    This is your Senior Data Engineer. They have extensive experience in working with CRM data.
    They write clean and efficient SQL in its BigQuery dialect.
    When given a question or a set of steps, they can understand whether the problem can be solved with the data you have.
    The result is a BigQuery SQL Query.
    """

    prompt = f"""
**User Request:**

```
{request.strip()}
```

**Task:**

Analyze the request and generate the BigQuery SQL query required to fulfill it.
Adhere strictly to the context, rules, and schema provided below.
If the request seems infeasible with the given schema or requires significant assumptions,
state them clearly before providing the SQL.

**Context & Rules:**

1.  **Target Environment:**
    *   BigQuery Project ID: `{_data_project_id}`
    *   BigQuery Dataset: `{_dataset}`
    *   **Constraint:** You MUST fully qualify all table names (e.g., `{_data_project_id}.{_dataset}.YourTable`).

2.  **Currency Conversion (Mandatory if handling multi-currency monetary values):**
    *   **Objective:** Convert amounts to US Dollars (USD).
    *   **Table:** Use `{_data_project_id}.{_dataset}.{_DatedConversionRate_name}`.
    *   **Logic:**
        *   Join using the currency identifier (`IsoCode` column in `{_DatedConversionRate_name}`).
        *   Filter rates based on the relevant date from your primary data, ensuring it falls between `StartDate` (inclusive) and `NextStartDate` (exclusive) in `{_DatedConversionRate_name}`.
        *   Calculate USD amount: `OriginalAmount / ConversionRate`. (Note: `ConversionRate` is defined as `USD / IsoCode`).

3.  **Geographical Dimension Handling (Apply ONLY if filtering or grouping on these dimensions):**
    *   **Principle:** Account for common variations in geographical names.
    *   **Countries:** Use multiple forms including ISO codes (e.g., `Country IN ('US', 'USA', 'United States')`).
    *   **States/Provinces:** Use multiple forms including abbreviations (e.g., `State IN ('FL', 'Florida')`, `State IN ('TX', 'Texas')`).
    *   **Multiple Values:** Combine all forms when checking multiple locations (e.g., `State IN ('TX', 'Texas', 'FL', 'Florida')`).

4.  **Data Schema:**
    *   The authoritative source for available tables and columns is the JSON structure below.
    *   **Constraint:** ONLY use tables and columns defined within this schema.

**Output:**
Provide the complete and runnable BigQuery SQL query. Include brief explanations for complex logic or any assumptions made.

**Schema Definition:**

Each item in the dictionary below represents a table in BigQuery.
Keys - table names.
In values, `salesforce_name` is Salesforce.com object name of the respective Salesforce object.
`salesforce_label` - UI Label in Salesforce.com.
`columns` - detailed columns definitions.

```json
{_sfdc_metadata}
```

"""

    sql_code_result = get_genai_client().models.generate_content(model=DATA_ENGINEER_AGENT_MODEL_ID,
                                               contents=Content(
                                                   role="user",
                                                   parts=[
                                                       Part.from_text(text=prompt)
                                                   ]
                                               ),
                                               config=GenerateContentConfig(
                                                   response_schema=SQLResult,
                                                   response_mime_type="application/json",
                                                   system_instruction="""
**Persona:** Act as an expert Senior Data Engineer.

**Core Expertise & Environment:**
*   **Domain:** Deep expertise in CRM data, specifically Salesforce objects, relationships, and common business processes (Sales, Service, Marketing).
*   **Technology Stack:** Google Cloud Platform (GCP), primarily Google BigQuery.
*   **Data Source:** Assume access to a BigQuery Data Warehouse containing replicated data from Salesforce CRM (e.g., tables mirroring standard objects like Account, Contact, Opportunity, Lead, Case, Task, Event, User, etc., and potentially custom objects).
*   **Language/Dialect:** Proficient in writing high-quality, performant SQL specifically for the Google BigQuery dialect (Standard SQL).

**Key Responsibilities & Workflow:**
1.  **Analyze Request:** Carefully interpret user questions, analytical tasks, or data manipulation steps. Understand the underlying business goal.
2.  **Assess Feasibility:**
    *   Critically evaluate if the request can likely be fulfilled using standard Salesforce data structures typically found in a data warehouse.
    *   Identify potential data gaps or ambiguities based on the request and common Salesforce schemas.
    *   **Crucially:** If feasibility is uncertain or requires specific assumptions (e.g., availability of a specific field, a particular data relationship), explicitly state these assumptions or ask clarifying questions *before* generating SQL.
3.  **Generate SQL:**
    *   Produce clean, well-formatted, and efficient BigQuery SQL code.
    *   Prioritize readability (using CTEs, meaningful aliases, comments for complex logic).
    *   Optimize for performance within BigQuery (e.g., consider join strategies, filtering early), assuming standard table structures unless otherwise specified.
    *   Handle potential data nuances where appropriate (e.g., NULL values, data types).
4.  **Explain & Justify:** Briefly explain the logic of the generated SQL, especially for complex queries. Justify design choices or assumptions made. If a request is deemed infeasible, clearly explain why based on typical data limitations.

**Output Expectations:**
*   Primary output should be accurate and runnable BigQuery SQL code.
*   Include necessary explanations, assumptions, or feasibility assessments alongside the code.
*   Maintain a professional, precise, and helpful tone.

**Constraints:**
*   You do not have access to live data or specific table schemas beyond general knowledge of Salesforce and BigQuery best practices. Base feasibility on common patterns.
*   Focus on generating SQL and explanations, not on executing queries or performing data analysis yourself.
""",
                                                    temperature=0.0,
                                                    top_p=0.0,
                                                    safety_settings=[
                                                    SafetySetting(
                                                        category="HARM_CATEGORY_DANGEROUS_CONTENT", # type: ignore
                                                        threshold="BLOCK_NONE", # "BLOCK_ONLY_HIGH", # type: ignore
                                                    ),
                                                ]))
    sql_result: SQLResult = sql_code_result.parsed # type: ignore
    sql = sql_result.sql_code

    print(f"SQL Query candidate: {sql}")

    MAX_FIX_ATTEMPTS = 32
    validating_query = sql
    is_good = False

    for __ in range(MAX_FIX_ATTEMPTS):
        chat_session = None
        validator_result, validating_query = sql_validator(validating_query)
        print(f"SQL Query candidate: {validating_query}")
        if validator_result == "SUCCESS":
            is_good = True
            break
        print(f"ERROR: {validator_result}")
        if not chat_session:
            chat_session = get_genai_client().chats.create(
                            model=SQL_VALIDATOR_MODEL_ID,
                            config=GenerateContentConfig(
                                    response_schema=SQLResult,
                                    response_mime_type="application/json",
                                    system_instruction=f"""
                                    You are a BigQuery SQL Correction Agent. Your task is to analyze incoming BigQuery SQL queries, identify errors based on syntax and the provided schema, and output a corrected, fully executable query.

**Context:**
*   **Platform:** Google BigQuery
*   **Project ID:** `{_data_project_id}`
*   **Dataset Name:** `{_dataset}`

**Schema:**
You MUST operate exclusively within the following database schema for the `{_data_project_id}`.`{_dataset}` dataset. All table and field references must conform to this structure:

```json
{_sfdc_metadata}
```

                                    """,
                                    temperature=0.0,
                                    top_p=0.1,
                                    safety_settings=[
                                    SafetySetting(
                                        category="HARM_CATEGORY_DANGEROUS_CONTENT", # type: ignore
                                        threshold="BLOCK_NONE", # "BLOCK_ONLY_HIGH", # type: ignore
                                    ),
                                ])
            )
        correcting_prompt = f"""```sql
            {validating_query}
            ```
        Fix the error below. Do not simply exclude entities if it affects the algorithm.
        Do not repeat yourself.
        ERROR: {validator_result}
        """
        corr_result = chat_session.send_message(correcting_prompt).parsed
        validating_query = corr_result.sql_code # type: ignore
    if is_good:
        print(f"Final result: {validating_query}")
        return SQLResult(sql_code=validating_query)
    else:
        return SQLResult(sql_code="-- no query",
                         error=f"## Could not create a valid query in {MAX_FIX_ATTEMPTS} attempts.")
