# CRM Data Q&A Agent

## Running the Agent in Cloud Shell

This tutorial will guide you through the agent demo deployment.

Click the **Start** button to move to the next step.

## Please select a project for deployment or create one

This project will be used:

- To make requests to Vertex AI API.
- To run BigQuery queries.

<walkthrough-project-setup billing="true"></walkthrough-project-setup>

## Run

### **For Demo installations only**

We can automatically create test datasets and artifacts for you in a few clicks.

Simply run this command in Cloud Shell:

```bash
gcloud config set project "<walkthrough-project-id/>"
src/_run.sh
```

## Conclusion

Thanks for trying our agent!

<walkthrough-conclusion-trophy></walkthrough-conclusion-trophy>
