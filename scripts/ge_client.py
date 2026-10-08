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

"""Converse with a registered A2UI agent through the Gemini Enterprise API.

Two transports are documented for an A2A agent registered in a Gemini Enterprise app:

* ``--via a2a`` (default, recommended): the per-agent A2A endpoint
  ``.../assistants/default_assistant/agents/{id}/a2a/v1/message:stream``. It accepts text
  parts only and joins them into one: a data part carrying the v0.9 action returned
  400 INVALID_ARGUMENT in tests in October 2026. Send a click as a ``Selected: name; k=v``
  text line (``--action-as text``, the default) with no other text, so the line reaches the
  agent's click parser unchanged.
* ``--via stream-assist``: ``.../assistants/default_assistant:streamAssist`` with
  ``agentsSpec.agentSpecs: [{agentId}]``. A click is a ``query.parts`` entry with
  ``mimeType`` ``application/json+a2ui`` and the action as a JSON string in
  ``uiJsonPayload``, next to a text part with the prompt. In tests in October 2026
  the default assistant answered these requests and they did not reach the agent;
  check the agent's request log before relying on this route.

Neither API returns the ``grounding_metadata`` an agent attaches; check the Google
Search entry point in the Gemini Enterprise app.

The reply's text is in the message content; the A2UI messages are in
``answer.replies[].groundedContent.content.inlineData`` (base64 ``application/json+a2ui``),
as Gemini Enterprise stored them. Pass the printed session back with ``--session`` to
continue the conversation (it is the A2A ``contextId``).

    uv run python scripts/ge_client.py --list
    uv run python scripts/ge_client.py \
        --agent "Trend Signals" "Open the trend workspace" --raw out.json
    uv run python scripts/ge_client.py \
        --agent <agent id> --session <session from previous turn> \
        --action-json '{"version":"v0.9","action":{"name":"ask","surfaceId":"...",
                        "context":{"prompt":"Recommend actions for Butter yellow"}}}'
    uv run python scripts/ge_client.py --via stream-assist --agent <agent id> "Open the trend workspace"

``--action-as text`` (the default) sends the click as a ``Selected: name; k=v`` text line, which
the click bridge in ``trend_signals.kit.actions`` routes; ``--action-as data`` sends the A2UI data
part that the Gemini Enterprise web app sends, for endpoints that accept it.

Config: GOOGLE_CLOUD_PROJECT, PROJECT_NUMBER, GEMINI_ENTERPRISE_APP_ID (from .env).
Auth: your ADC user token (gcloud auth application-default login) + x-goog-user-project.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import google.auth
import google.auth.transport.requests
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
PROJECT_NUMBER = os.getenv("PROJECT_NUMBER", "")
LOCATION = os.getenv("DISCOVERY_ENGINE_LOCATION", "global")
ENGINE = os.getenv("GEMINI_ENTERPRISE_APP_ID", "")
_missing = [k for k, v in (("GOOGLE_CLOUD_PROJECT", PROJECT), ("PROJECT_NUMBER", PROJECT_NUMBER),
                           ("GEMINI_ENTERPRISE_APP_ID", ENGINE))
            if v in ("", "your-project-id", "your-ge-app-id")]
if _missing:
    sys.exit(f"Set {', '.join(_missing)} in .env (see .env.example), then retry.")
HOST = "https://discoveryengine.googleapis.com"
A2UI_MIME = "application/json+a2ui"

_creds = None


def _headers() -> dict[str, str]:
    global _creds
    if _creds is None:
        _creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    if not _creds.valid:
        _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
        "x-goog-user-project": PROJECT,
    }


def assistant_path(engine: str = ENGINE) -> str:
    return (f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/collections/default_collection"
            f"/engines/{engine}/assistants/default_assistant")


def _check(r: requests.Response) -> requests.Response:
    if r.status_code >= 400:
        raise SystemExit(f"GE API {r.status_code} {r.request.method} {r.url}\n{r.text[:2000]}")
    return r


def list_agents(engine: str = ENGINE) -> list[dict]:
    url = f"{HOST}/v1alpha/{assistant_path(engine)}/agents"
    return _check(requests.get(url, headers=_headers(), timeout=60)).json().get("agents", [])


def resolve_agent_id(agent: str, engine: str = ENGINE) -> tuple[str, str]:
    """Accept an agent id or an exact / unique-substring display name."""
    by_id = {a["name"].rsplit("/", 1)[-1]: a.get("displayName", "") for a in list_agents(engine)}
    if agent in by_id:
        return agent, by_id[agent]
    hits = [(i, n) for i, n in by_id.items() if n == agent] or \
           [(i, n) for i, n in by_id.items() if agent.lower() in n.lower()]
    if len(hits) != 1:
        raise SystemExit(f"Agent {agent!r} matched {len(hits)} of: {json.dumps(by_id, indent=1)}")
    return hits[0]


def a2a_url(agent_id: str, engine: str = ENGINE) -> str:
    return f"{HOST}/v1/{assistant_path(engine)}/agents/{agent_id}/a2a"


def selected_line(action_msg: dict) -> str:
    """v0.9 client action -> the ``Selected: name; k=v`` line our click bridge routes."""
    ua = action_msg.get("action") or action_msg.get("userAction") or action_msg
    ctx = ua.get("context") or {}
    kvs = "".join(f"; {k}={','.join(map(str, v)) if isinstance(v, list) else v}"
                  for k, v in ctx.items() if v is not None)
    return f"Selected: {ua['name']}{kvs}"


def click_prompt(action_msg: dict) -> str:
    """The text Gemini Enterprise sends with a click: the action's context.prompt."""
    ua = action_msg.get("action") or action_msg.get("userAction") or action_msg
    return str((ua.get("context") or {}).get("prompt") or "User action triggered.")


def send(agent_id: str, texts: list[str], *, action: dict | None = None, action_as: str = "text",
         session: str | None = None, engine: str = ENGINE, timeout: float = 300.0) -> tuple[list[dict], float]:
    """One turn via the agent's A2A endpoint (message:stream). Returns (raw chunks, seconds)."""
    content: list[dict[str, Any]] = [{"text": t} for t in texts]
    if action is not None:
        if action_as == "text":
            content.append({"text": selected_line(action)})
        else:
            content += [{"text": click_prompt(action)},
                        {"data": {"data": action}, "metadata": {"mimeType": A2UI_MIME}}]
    message: dict[str, Any] = {"role": "ROLE_USER", "messageId": uuid.uuid4().hex, "content": content}
    if session:
        message["contextId"] = session
    t0 = time.perf_counter()
    r = _check(requests.post(f"{a2a_url(agent_id, engine)}/v1/message:stream",
                             headers=_headers(), json={"message": message}, timeout=timeout))
    elapsed = time.perf_counter() - t0
    data = r.json()
    return (data if isinstance(data, list) else [data]), elapsed


def stream_assist(agent_id: str, texts: list[str], *, action: dict | None = None, session: str | None = None,
                  engine: str = ENGINE, timeout: float = 300.0) -> tuple[list[dict], float]:
    """One turn via streamAssist, routed to the agent with agentsSpec. Returns (raw chunks, seconds)."""
    parts: list[dict[str, Any]] = [{"text": t} for t in texts]
    if action is not None:
        parts += [{"text": click_prompt(action)},
                  {"mimeType": A2UI_MIME, "uiJsonPayload": json.dumps(action)}]
    body: dict[str, Any] = {"query": {"parts": parts},
                            "agentsSpec": {"agentSpecs": [{"agentId": agent_id}]}}
    if session:
        body["session"] = session
    t0 = time.perf_counter()
    r = _check(requests.post(f"{HOST}/v1alpha/{assistant_path(engine)}:streamAssist",
                             headers=_headers(), json=body, timeout=timeout))
    elapsed = time.perf_counter() - t0
    data = r.json()
    return (data if isinstance(data, list) else [data]), elapsed


def session_turns(session: str) -> list[dict]:
    """The session as GE stored it (query parts + detailed answers)."""
    r = _check(requests.get(f"{HOST}/v1alpha/{session}", headers=_headers(),
                            params={"includeAnswerDetails": True}, timeout=60))
    return r.json().get("turns", [])


def _decode(blob: dict) -> Any:
    raw = blob.get("data", "")
    try:
        raw = base64.b64decode(raw).decode("utf-8")
    except Exception:
        pass
    try:
        return json.loads(raw)
    except Exception:
        return raw


def summarize(chunks: list[dict]) -> dict:
    """Text, A2UI / other data blobs, answer state, agent and session from a stream."""
    content_text: list[str] = []
    reply_text: list[str] = []
    blobs: list[dict] = []
    session = state = agent = None
    extras: dict[str, Any] = {}
    for ch in chunks:
        msg = ch.get("message") or {}  # message:stream wraps the answer in an A2A message
        session = msg.get("contextId") or (ch.get("sessionInfo") or {}).get("session") or session
        content_text += [c["text"] for c in msg.get("content", []) if c.get("text")]
        meta = msg.get("metadata") or {}
        ans = meta.get("answer") or ch.get("answer") or {}
        state = ans.get("state", state)
        agent = (meta.get("agentInfo") or {}).get("displayName", agent)
        for k in ("assistSkippedReasons", "customerPolicyEnforcementResult"):
            if ans.get(k):
                extras[k] = ans[k]
        for k in set(ch) - {"message", "answer", "sessionInfo", "assistToken"}:
            extras[k] = ch[k]
        for rep in ans.get("replies", []) or []:
            c = (rep.get("groundedContent") or {}).get("content") or {}
            if c.get("text") and not c.get("thought"):
                reply_text.append(c["text"])
            if c.get("inlineData"):
                blobs.append({"mimeType": c["inlineData"].get("mimeType"),
                              "payload": _decode(c["inlineData"])})
    return {"text": "".join(content_text).strip() or "".join(reply_text).strip(),
            "blobs": blobs, "session": session, "state": state, "agent": agent,
            "extras": extras}


def describe_a2ui(msg: dict) -> list[str]:
    ver = f"[{msg['version']}] " if msg.get("version") else ""
    if "createSurface" in msg:
        b = msg["createSurface"]
        return [f"{ver}createSurface {b.get('surfaceId')} catalog={b.get('catalogId')}"]
    if "updateComponents" in msg:
        comps = msg["updateComponents"].get("components", [])
        types: dict[str, int] = {}
        actions = []
        for c in comps:
            types[c.get("component")] = types.get(c.get("component"), 0) + 1
            ev = (c.get("action") or {}).get("event")
            if ev:
                actions.append(f"{c.get('id')}->{ev.get('name')}{json.dumps(ev.get('context') or {})}")
        lines = [f"{ver}updateComponents {msg['updateComponents'].get('surfaceId')} "
                 f"{len(comps)} components {json.dumps(types)}"]
        lines += [f"    action {a}" for a in actions]
        return lines
    if "updateDataModel" in msg:
        b = msg["updateDataModel"]
        return [f"{ver}updateDataModel {b.get('surfaceId')} path={b.get('path')} "
                f"value={json.dumps(b.get('value'))[:300]}"]
    return [f"{ver}{json.dumps(msg)[:300]}"]


def print_turn(name: str, agent_id: str, secs: float, chunks: list[dict]) -> dict:
    s = summarize(chunks)
    print(f"agent:   {name} ({agent_id})   answered-by: {s['agent']}")
    print(f"latency: {secs:.1f}s   chunks: {len(chunks)}   state: {s['state']}")
    for k, v in s["extras"].items():
        print(f"GE {k}: {json.dumps(v)[:600]}")
    print(f"\n--- text ---\n{s['text'] or '(none)'}\n")
    print(f"--- blobs ({len(s['blobs'])}) ---")
    for b in s["blobs"]:
        if b["mimeType"] == A2UI_MIME and isinstance(b["payload"], dict):
            for line in describe_a2ui(b["payload"]):
                print(f"  {line}")
        else:
            print(f"  {b['mimeType']}: {json.dumps(b['payload'])[:400]}")
    print(f"\nsession: {s['session']}")
    return s


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("message", nargs="?", help="user text for this turn")
    ap.add_argument("--agent", help="agent id or display name (substring ok if unique)")
    ap.add_argument("--session", help="session name (contextId) from a previous turn")
    ap.add_argument("--action-json", help="A2UI v0.9 client action message to send as a click")
    ap.add_argument("--action-as", choices=["data", "text"], default="text",
                    help="--via a2a only: send the click as a Selected: text line (default) or an A2UI data part")
    ap.add_argument("--via", choices=["a2a", "stream-assist"], default="a2a",
                    help="the agent's A2A endpoint (default) or streamAssist with agentsSpec")
    ap.add_argument("--raw", help="write the raw streamed response JSON here")
    ap.add_argument("--show-session", action="store_true",
                    help="print what GE stored for the last turn's query (parts)")
    ap.add_argument("--engine", default=ENGINE)
    ap.add_argument("--list", action="store_true", help="list registered agents and exit")
    args = ap.parse_args()

    if args.list:
        for a in list_agents(args.engine):
            print(f"{a['name'].rsplit('/', 1)[-1]:>22}  {a.get('displayName')}  [{a.get('state', '')}]")
        return
    if not args.agent or not (args.message or args.action_json):
        ap.error("--agent and a message (or --action-json) are required")

    agent_id, name = resolve_agent_id(args.agent, args.engine)
    texts = [args.message] if args.message else []
    action = json.loads(args.action_json) if args.action_json else None
    if args.via == "stream-assist":
        chunks, secs = stream_assist(agent_id, texts, action=action, session=args.session, engine=args.engine)
    else:
        chunks, secs = send(agent_id, texts, action=action, action_as=args.action_as, session=args.session,
                            engine=args.engine)
    if args.raw:
        with open(args.raw, "w") as f:
            json.dump(chunks, f, indent=2)
    s = print_turn(name, agent_id, secs, chunks)
    if args.show_session and s["session"]:
        print(f"\nGE-stored query: {json.dumps(session_turns(s['session'])[-1].get('query'), indent=1)}")


if __name__ == "__main__":
    sys.exit(main())
