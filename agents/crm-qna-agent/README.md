# CRM Data Q&A Agent

It can answer business questions using CRM data.

Do not ask questions about data. Ask questions about your business.

Examples:

* "Top 5 customers in every country"
* "What are our best lead sources?"
  * or more specific "What are our best lead sources by value?"
* Lead conversion trends in the US.

## Deploy and Run

### Running the demo

#### In Google Cloud Shell

Use this magic button to run this agent in Cloud Shell, and follow the tutorial!

[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/cloudshell/?terminal=true&show=terminal&cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fvladkol%2Fadk-samples&cloudshell_git_branch=vladkol%2Fcrm-qna-agent&cloudshell_tutorial=tutorial%2Fdeployment.md&cloudshell_workspace=agents%2Fcrm-qna-agent)

> If facing issues (e.g. `marshal data too short` error), try [Ephemeral Mode](https://shell.cloud.google.com/cloudshell/?terminal=true&show=terminal&cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fvladkol%2Fadk-samples&cloudshell_git_branch=vladkol%2Fcrm-qna-agent&cloudshell_tutorial=tutorial%2Fdeployment.md&cloudshell_workspace=agents%2Fcrm-qna-agent&ephemeral=true).

#### Running it locally

> Use a Python Virtual Environment. Don't forget to a activate it.

* [Optional] Edit `src/_run.sh` with your environment variables. For running a demo, only really only may need to change `GOOGLE_CLOUD_PROJECT` configuration variable.

* Run `src/run_web.sh` (or `src/run_streamlit.sh` for custom Streamlit-based UI).
* Navigate to `http://localhost:8080`.

> You can also simply run `adk web` from your `agents` directory. Make sure you install dependencies before that: `pip install -r agents/crm-qna-agent/src/agents/qna_agent/requirements.txt`.

### Deploying the Agent to Cloud Run

* Edit `src/_deploy.sh` with your environment variables.

For running in demo mode, only change `GOOGLE_CLOUD_PROJECT` configuration variable.

> The respective Cloud Project must have Vertex AI and BigQuery APIs enabled:

```bash
gcloud services enable \
    aiplatform.googleapis.com \
    bigquery.googleapis.com \
    --project ${GOOGLE_CLOUD_PROJECT}
```

* Run `src/_deploy.sh`.

### Deployment with a real Salesforce.com instance

*COMING SOON!*

We will use:

* [Salesforce transfer](https://cloud.google.com/bigquery/docs/salesforce-transfer) in BigQuery Data Transfer Service for getting Salesforce.com data.
* [Simple Salesforce](https://github.com/simple-salesforce/simple-salesforce) library for retrieving your Salesforce metadata.

You can take a look in [`metadata/sfdc_metadata_loader`](metadata/sfdc_metadata_loader/sfdc_metadata_loader.py)
