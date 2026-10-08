#!/usr/bin/env bash
# Copyright 2026 Google LLC
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

# Deploy the Trend Signals agent to Cloud Run (builds the image from source).
#
#   ./deploy/deploy_cloud_run.sh
#
# Required env: GOOGLE_CLOUD_PROJECT (or PROJECT_ID).
# Optional env: REGION, SERVICE, MODEL, MAX_HOPS_PER_TURN, MIN_INSTANCES, MAX_INSTANCES.
# MAX_INSTANCES defaults to 1: the workspace state is held in memory (src/trend_signals/ui_state.py), so
# one conversation must reach one instance. Move that state to a shared store before raising it.
# gcloud runs as your active account (gcloud config set account ...).
#
# Gemini Enterprise security-checks the agent card host, so APP_URL must be the service's
# STABLE URL (the one containing the project number), never the hashed one. Cloud Run lists
# both in the run.googleapis.com/urls annotation; the script reads it (after the first deploy,
# once the service exists) and pins APP_URL.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-${GOOGLE_CLOUD_PROJECT:-}}"
[[ -n "$PROJECT_ID" && "$PROJECT_ID" != "your-project-id" ]] || {
  echo "GOOGLE_CLOUD_PROJECT is not set: copy .env.example to .env and fill it in" >&2; exit 1; }
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-trend-signals-agent}"
SA_NAME="trend-signals-sa"
SA="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
MODEL="${MODEL:-gemini-3.7-flash}"

GC=(gcloud --project "$PROJECT_ID")
PROJECT_NUMBER=$("${GC[@]}" projects describe "$PROJECT_ID" --format='value(projectNumber)')

# The stable URL of $SERVICE, or nothing when the service does not exist yet.
stable_url() {
  "${GC[@]}" run services describe "$SERVICE" --region "$REGION" \
    --format='value(metadata.annotations."run.googleapis.com/urls")' 2>/dev/null \
    | tr -d '[]" ' | tr ',' '\n' | grep -- "-${PROJECT_NUMBER}\." || true
}
STABLE_URL=$(stable_url)

echo "== ${SERVICE} -> ${PROJECT_ID}/${REGION}"

# ---- runtime service account + role (idempotent) ------------------------------------
if ! "${GC[@]}" iam service-accounts describe "$SA" >/dev/null 2>&1; then
  "${GC[@]}" iam service-accounts create "$SA_NAME" --display-name="Trend Signals agent runtime"
  echo "created ${SA}; waiting for propagation"; sleep 20
fi
"${GC[@]}" projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA}" --role="roles/aiplatform.user" --condition=None --quiet >/dev/null

# ---- deploy ----------------------------------------------------------------------------
"${GC[@]}" run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --service-account "$SA" \
  --no-allow-unauthenticated \
  --port 8080 \
  --memory 2Gi --cpu 2 \
  --no-cpu-throttling --cpu-boost \
  --concurrency 8 --timeout 300 \
  --min-instances "${MIN_INSTANCES:-0}" \
  --max-instances "${MAX_INSTANCES:-1}" \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=global,GOOGLE_GENAI_USE_VERTEXAI=true,MODEL=${MODEL},MAX_HOPS_PER_TURN=${MAX_HOPS_PER_TURN:-10},APP_URL=${STABLE_URL},AGENT_URL=${STABLE_URL}"

# First deploy: the URL exists only now. Pin it (creates one more revision).
if [[ -z "$STABLE_URL" ]]; then
  STABLE_URL=$(stable_url)
  [[ -n "$STABLE_URL" ]] || { echo "Could not read the stable URL of ${SERVICE} (run.googleapis.com/urls annotation)" >&2; exit 1; }
  "${GC[@]}" run services update "$SERVICE" --region "$REGION" \
    --update-env-vars "APP_URL=${STABLE_URL},AGENT_URL=${STABLE_URL}"
fi

# ---- Gemini Enterprise invoker (the Discovery Engine service agent must call the service) --
"${GC[@]}" run services add-iam-policy-binding "$SERVICE" \
  --region "$REGION" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
  --role="roles/run.invoker" --quiet >/dev/null

echo "== deployed: ${STABLE_URL}"
echo "== next: make register (re-run it after any agent-card change)"
