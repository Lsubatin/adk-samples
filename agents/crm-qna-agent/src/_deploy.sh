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

export AGENT_NAME="qna_agent"
GOOGLE_CLOUD_PROJECT="$(gcloud config get-value project -q)"
export GOOGLE_CLOUD_PROJECT
export GOOGLE_CLOUD_LOCATION="us-central1"
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

adk deploy cloud_run \
    --service_name=qna-agent-service \
    --project "${GOOGLE_CLOUD_PROJECT}" \
    --region "${GOOGLE_CLOUD_LOCATION}" \
    "${SCRIPT_DIR}/agents/${AGENT_NAME}"
