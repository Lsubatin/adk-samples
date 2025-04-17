# CRM Data Q&A Agent

## Running and Deploying the Agent in Cloud Shell

This tutorial will guide you through the agent deployment.

Click the **Start** button to move to the next step.

## Please select a project for deployment or create one

This project will be used:

- To make requests to Vertex AI API.
- To run BigQuery queries.

<walkthrough-project-setup billing="true"></walkthrough-project-setup>

## Running the agent

### Run demo in Cloud Shell

#### Run ADK Web UI

Simply run this command in Cloud Shell:

```bash
gcloud config set project "<walkthrough-project-id/>"
src/run_web.sh
```

#### Run with custom streamlit UI

Simply run this command in Cloud Shell:

```bash
gcloud config set project "<walkthrough-project-id/>"
src/run_streamlit.sh
```

### Deploy to Cloud Run

To deploy the agent to Cloud Run, run this command in Cloud Shell:

```bash
gcloud config set project "<walkthrough-project-id/>"
src/_deploy.sh
```

## Conclusion

Thanks for trying our agent!

If you are running it here, open <walkthrough-spotlight-pointer spotlightId="cloud-shell-web-preview-button">Cloud Shell Web Preview</walkthrough-spotlight-pointer>!

<walkthrough-conclusion-trophy></walkthrough-conclusion-trophy>
