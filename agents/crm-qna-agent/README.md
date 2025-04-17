# CRM Data Q&A Agent

It can answer business questions using CRM data.

Do not ask questions about data. Ask questions about your business.

## Deploy and Run

### Running demo in Google Cloud Shell or locally

Use this magic button to run this agent in Cloud Shell

[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/cloudshell/?terminal=true&show=terminal&cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fvladkol%2Fadk-samples&cloudshell_git_branch=vladkol%2Fcrm-qna-agent&cloudshell_tutorial=tutorial%2Fdeployment.md&cloudshell_workspace=agents%2Fcrm-qna-agent)

> Use a Python Virtual Environment. Don't forget to a activate it.
> I like using [`uv`](https://docs.astral.sh/uv/#installation).

* [Optional] Edit `src/_run.sh` with your environment variables. For running a demo, only really only may need to change `GOOGLE_CLOUD_PROJECT` configuration variable.

> If running in Cloud Shell, don't change the variable. Select proper active project in Terminal instead.
If facing issues (e.g. `marshal data too short` error), try [Ephemeral Mode](https://shell.cloud.google.com/cloudshell/?terminal=true&show=terminal&cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fvladkol%2Fadk-samples&cloudshell_git_branch=vladkol%2Fcrm-qna-agent&cloudshell_tutorial=tutorial%2Fdeployment.md&cloudshell_workspace=agents%2Fcrm-qna-agent&ephemeral=true).

* Enable Vertex AI and BigQuery APIs

```bash
gcloud services enable \
    aiplatform.googleapis.com \
    bigquery.googleapis.com
```

> Add `--project=YOUR_ANOTHER_PROJECT_ID` if you change `GOOGLE_CLOUD_PROJECT` in `src/_run.sh`

* Run `src/_run.sh`.
* Navigate to `http://localhost:8501` (or in [Cloud Shell Web Preview](https://cloud.google.com/shell/docs/using-web-preview)).
* Ask the agent questions that can be answered with CRM data.

### Deployment the Agent to Cloud Run

* Edit `src/_run.sh` with your environment variables.

For running a demo, only change `GOOGLE_CLOUD_PROJECT` configuration variable.

> The respective Cloud Project must have Vertex AI and BigQuery APIs enabled:

```bash
gcloud services enable \
    aiplatform.googleapis.com \
    bigquery.googleapis.com \
    --project ${GOOGLE_CLOUD_PROJECT}
```

* Run `src/_run.sh`.
* Navigate to `http://localhost:8080`. Ask questions that can be answered with CRM data.

### Deployment with a real Salesforce.com instance

*COMING SOON!*

We will use:

* [Salesforce transfer](https://cloud.google.com/bigquery/docs/salesforce-transfer) in BigQuery Data Transfer Service for getting Salesforce.com data.
* [Simple Salesforce](https://github.com/simple-salesforce/simple-salesforce) library for retrieving your Salesforce metadata.

You can take a look in [`metadata/sfdc_metadata_loader`](metadata/sfdc_metadata_loader/sfdc_metadata_loader.py)
