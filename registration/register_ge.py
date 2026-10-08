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

"""Register the deployed Trend Signals agent in a Gemini Enterprise app (engine).

The agent card is built by the same code the service runs (`trend_signals.card`) with the
service's stable URL, so the card Gemini Enterprise stores cannot drift from the live one.
Gemini Enterprise keeps a static copy of the card: run this again after ANY card change.

    uv run python registration/register_ge.py register [--dry-run]
    uv run python registration/register_ge.py list
    uv run python registration/register_ge.py delete

Config (.env): GOOGLE_CLOUD_PROJECT, GEMINI_ENTERPRISE_APP_ID, DISCOVERY_ENGINE_LOCATION,
REGION, SERVICE (default trend-signals-agent). Auth: your ADC (gcloud auth application-default login).
Registration is idempotent: an agent with the same display name is updated, otherwise created.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

ICON = "https://fonts.gstatic.com/s/i/short-term/release/materialsymbolsoutlined/insights/default/48px.svg"


def _need(name: str) -> str:
    v = os.environ.get(name, "")
    if v in ("", "your-project-id", "your-ge-app-id"):
        sys.exit(f"{name} is not set: copy .env.example to .env and fill it in.")
    return v


def _request(method: str, url: str, project: str, body: dict | None = None) -> dict:
    import google.auth
    import google.auth.transport.requests

    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    headers = {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json",
               "X-Goog-User-Project": project}
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            text = resp.read().decode()
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} from {method} {url}\n{e.read().decode()}")


def _agents_url(project: str, location: str, engine: str) -> str:
    host = "https://discoveryengine.googleapis.com" if location == "global" \
        else f"https://{location}-discoveryengine.googleapis.com"
    return (f"{host}/v1alpha/projects/{project}/locations/{location}/collections/default_collection"
            f"/engines/{engine}/assistants/default_assistant/agents")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["register", "list", "delete"])
    ap.add_argument("--dry-run", action="store_true", help="print the request body, call nothing")
    args = ap.parse_args()

    project = _need("GOOGLE_CLOUD_PROJECT")
    engine = _need("GEMINI_ENTERPRISE_APP_ID")
    location = os.environ.get("DISCOVERY_ENGINE_LOCATION", "global")
    service = os.environ.get("SERVICE", "trend-signals-agent")
    base = _agents_url(project, location, engine)

    if args.command == "list":
        for a in _request("GET", base, project).get("agents", []):
            print(f"{a['name'].rsplit('/', 1)[-1]}  {a.get('displayName')}  [{a.get('state', '')}]")
        return

    if args.command == "register":
        from cloud_run_url import stable_url

        url = stable_url(service, project=project, region=os.environ.get("REGION", "us-central1"))
        os.environ["AGENT_URL"] = url  # the card builder reads it when trend_signals.kit.config is imported

    from trend_signals import card  # light: no ADK import

    existing = next((a for a in _request("GET", base, project).get("agents", [])
                     if a.get("displayName") == card.DISPLAY_NAME), None)
    if args.command == "delete":
        if not existing:
            sys.exit(f"No agent named {card.DISPLAY_NAME!r} in {engine}.")
        _request("DELETE", f"https://discoveryengine.googleapis.com/v1alpha/{existing['name']}", project)
        print(f"deleted {existing['name']}")
        return

    agent_card = card.build_agent_card().model_dump(by_alias=True, exclude_none=True, mode="json")
    body = {
        "displayName": card.DISPLAY_NAME,
        "description": card.DESCRIPTION,
        "a2aAgentDefinition": {"jsonAgentCard": json.dumps(agent_card)},
        "customPlaceholderText": 'Try "Open the trend workspace"',
        "starterPrompts": [{"text": t} for t in card.STARTER_PROMPTS],
        "icon": {"uri": ICON},
    }
    mask = "description,a2aAgentDefinition,customPlaceholderText,starterPrompts,icon"
    print(f"Engine : {engine}  (project {project}, location {location})\nService: {service} -> {url}")
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return
    if existing:
        out = _request("PATCH", f"https://discoveryengine.googleapis.com/v1alpha/{existing['name']}"
                                f"?updateMask={urllib.parse.quote(mask)}", project, body)
        print(f"updated {out.get('name')}")
    else:
        out = _request("POST", base, project, body)
        print(f"created {out.get('name')}")


if __name__ == "__main__":
    main()
