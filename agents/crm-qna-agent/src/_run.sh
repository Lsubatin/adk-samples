#!/bin/bash
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

# FOR DEPLOYING A DEMO, ONLY EDIT THESE CONFIGURATION VARIABLES
###############################################################################
export GOOGLE_GENAI_USE_VERTEXAI=1 # Use Vertex AI

# Current project or type your project's name. Must have aiplatform.googleapis.com API enabled.
GOOGLE_CLOUD_PROJECT="$(gcloud config get-value project -q)"
export GOOGLE_CLOUD_PROJECT

export GOOGLE_CLOUD_LOCATION="us-central1" # Cloud region to use Vertex AI in.
export PORT=8080 # Streamlit app port.

####################### Salesforce.com Data in BigQuery #######################

# If you have have your own Salesforce.com data replicated using BQ DTS,
# change 3 variables below.
# If running your agent as a service, the service account must have read access to SFDC_BQ_PROJECT_ID.
export SFDC_BQ_PROJECT_ID="kittycorn-public" # BigQuery project ID. `kittycorn-public` has public sample datasets.
export BQ_PROJECT_ID="${GOOGLE_CLOUD_PROJECT}" # Data SFDC_BQ_PROJECT_ID, but queries run in BQ_PROJECT_ID.
export BQ_DATASET="sfdc__raw__6_3__us" # BigQuery dataset name
export BQ_LOCATION="US" # BigQuery dataset location/region

# If you know how to generate Salesforce.com metadata, this is path to the metadata file.
# By default, `sfdc_metadata.json` in qna_agent folder is used (it has most popular objects and standard fields).
export SFDC_METADATA_FILE="sfdc_metadata.json"

###############################################################################
export AGENT_NAME="qna_agent"
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo "Using project ${GOOGLE_CLOUD_PROJECT}"

pushd "${SCRIPT_DIR}/agents" &> /dev/null || exit

echo "Installing dependencies..."
pip install -r "${AGENT_NAME}/requirements.txt" &> /dev/null

echo "Running..."
if [[ "${1}" == "streamlit" ]]; then
    python3 main.py "${AGENT_NAME}"
else
    python3 -m google.adk.cli web --port "${PORT}"
fi

popd &> /dev/null || exit
