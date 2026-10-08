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

"""Environment configuration.

Load-bearing invariant: ``GOOGLE_CLOUD_LOCATION`` must be ``global`` — Gemini 3.x on
Vertex AI is served from the global endpoint only; a regional value returns 404. It is
forced at import time, before any google-genai client is constructed.
"""

from __future__ import annotations

import os

os.environ["GOOGLE_CLOUD_LOCATION"] = "global"

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "")
LOCATION = "global"
MODEL = os.getenv("MODEL", "gemini-3.7-flash")

# Public base URL of THIS Cloud Run service. It must be the stable
# https://<service>-<project-number>.<region>.run.app host: Gemini Enterprise
# security-checks the agent card host and blocks mismatches.
APP_URL = os.getenv("APP_URL", os.getenv("AGENT_URL", "http://localhost:8080"))
AGENT_URL = os.getenv("AGENT_URL", APP_URL)


# Where the built single-file Vite bundle lives (the Dockerfile copies it here).
FRONTEND_DIST = os.getenv("FRONTEND_DIST", "frontend/dist")

# Wall-clock budget for one agent turn. Gemini Enterprise gives up on a slow agent ("connection to the
# server was lost"), so the executor stops first and says so. MODEL_CALL_TIMEOUT_MS bounds one model call.
TURN_TIMEOUT_S = float(os.getenv("TURN_TIMEOUT_S", "85"))
MODEL_CALL_TIMEOUT_MS = int(os.getenv("MODEL_CALL_TIMEOUT_MS", "40000"))

# Most model calls the agent may make in one turn (tool calls included).
MAX_HOPS_PER_TURN = int(os.getenv("MAX_HOPS_PER_TURN", "10"))


def require_project() -> None:
    """Fail at startup, with the fix, when the model project is not configured."""
    if PROJECT_ID and PROJECT_ID != "your-project-id":
        return
    raise SystemExit(
        "GOOGLE_CLOUD_PROJECT is not set. Copy .env.example to .env and set it "
        "(the project whose Vertex AI serves the Gemini model)."
    )
