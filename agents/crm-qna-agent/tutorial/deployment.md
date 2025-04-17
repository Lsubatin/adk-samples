# CRM Data Q&A Agent

The agent can answer business questions using CRM data.
Do not ask questions about data. Ask questions about your business.

## Running and Deploying the Agent in Cloud Shell

This tutorial will guide you through the agent demo and deployment.

Click the **Start** button to move to the next step.

## Please select a project for deployment or create one

This project will be used:

- To make requests to Vertex AI API.
- To run BigQuery queries.

<walkthrough-project-setup billing="true"></walkthrough-project-setup>

## Running the agent

### Run demo in Cloud Shell

Choose **one** of the options below

#### Option 1: Run ADK Web UI

- Run this command in Terminal:

```bash
gcloud config set project "<walkthrough-project-id/>"
src/run_web.sh
```

- Wait for `ADK Web Server started` text in the Terminal.
- Open <walkthrough-spotlight-pointer spotlightId="cloud-shell-web-preview-button">Cloud Shell Web Preview</walkthrough-spotlight-pointer>.

#### Option 2: Run with custom Streamlit UI

- Run this command in Terminal:

```bash
gcloud config set project "<walkthrough-project-id/>"
src/run_streamlit.sh
```

- Wait for `You can now view your Streamlit app in your browser` text in the Terminal.
- Open <walkthrough-spotlight-pointer spotlightId="cloud-shell-web-preview-button">Cloud Shell Web Preview</walkthrough-spotlight-pointer>.

### Deploy to Cloud Run

To deploy the agent to Cloud Run, run this command in Terminal:

```bash
gcloud config set project "<walkthrough-project-id/>"
src/_deploy.sh
```

## Conclusion

Thanks for trying our CRM Data Q&A Agent!

The agent can answer business questions using CRM data.
Do not ask questions about data. Ask questions about your business.

<walkthrough-conclusion-trophy></walkthrough-conclusion-trophy>
