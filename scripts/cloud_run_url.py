#!/usr/bin/env python3
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

"""Look up the stable URL of a deployed Cloud Run service.

A Cloud Run service has two URLs: a hashed one and a stable one that contains
the project number. Gemini Enterprise security-checks the agent card host, so
the agents advertise the stable one. Cloud Run lists both in the service's
``run.googleapis.com/urls`` annotation; this picks the one with the project
number. It never guesses: an undeployed service is an error with a fix hint.

    uv run python scripts/cloud_run_url.py trend-signals-agent

Config: GOOGLE_CLOUD_PROJECT, REGION (default us-central1), PROJECT_NUMBER
(looked up with gcloud when empty).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys


def _gcloud(*args: str) -> str:
    try:
        out = subprocess.run(["gcloud", *args], capture_output=True, text=True, check=True,
                             timeout=60)
    except FileNotFoundError:
        sys.exit("gcloud is not installed: https://cloud.google.com/sdk/docs/install")
    except subprocess.CalledProcessError as e:
        sys.exit(f"gcloud {' '.join(args[:3])} failed:\n{e.stderr.strip()}")
    return out.stdout.strip()


def project_number(project: str) -> str:
    num = os.environ.get("PROJECT_NUMBER", "") or _gcloud(
        "projects", "describe", project, "--format=value(projectNumber)")
    if not num:
        sys.exit(f"Could not resolve the project number of '{project}'. Set PROJECT_NUMBER in .env.")
    return num


def stable_url(service: str, project: str | None = None, region: str | None = None) -> str:
    project = project or os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    region = region or os.environ.get("REGION", "us-central1")
    if not project:
        sys.exit("GOOGLE_CLOUD_PROJECT is not set: cp .env.example .env and fill it in.")
    raw = _gcloud("run", "services", "describe", service, "--project", project,
                  "--region", region, "--format=json")
    annotations = (json.loads(raw).get("metadata") or {}).get("annotations") or {}
    urls = json.loads(annotations.get("run.googleapis.com/urls", "[]"))
    marker = f"-{project_number(project)}."
    for url in urls:
        if marker in url:
            return url
    sys.exit(f"Cloud Run service '{service}' in {project}/{region} lists no stable URL "
             f"({urls}). Deploy it first with deploy/deploy_cloud_run.sh.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(stable_url(sys.argv[1]))
