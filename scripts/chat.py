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

"""Talk to the agent directly over A2A, the way Gemini Enterprise does, and show what comes back.

    uv run python scripts/chat.py "Where are my biggest whitespace gaps?"
    uv run python scripts/chat.py --url http://localhost:8080 "hi"
    uv run python scripts/chat.py --service trend-signals-agent "Compare Butter yellow and Barrel-leg denim"

A canvas click is sent as Gemini Enterprise sends it: a text part with the prompt and a v0.9 action
data part whose context is the canvas state.

    uv run python scripts/chat.py --action ask --ctx '{"view":"detail","sel":"t02","board":"-"}' \
        "Recommend actions for Barrel-leg denim"

For each reply it prints the chat text, the suggestion chips and a summary of the Canvas: the view the
page was opened on and what the agent put into it. Pass --context to continue a conversation.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from smoke_remote import _id_token  # noqa: E402

A2UI = "application/json+a2ui"
SUGGEST = "application/json+suggestions"
KEY = "window.__TREND_SIGNALS_STATE__="


def canvas_summary(messages: list[dict]) -> str:
    out = []
    for m in messages:
        comps = (m.get("updateComponents") or {}).get("components") or []
        for c in comps:
            html = c.get("htmlContent")
            if c.get("component") == "IFrameSrcdoc" and html and KEY in html:
                st = json.loads(html.split(KEY, 1)[1].split(";</script>", 1)[0].replace("<\\/", "</"))
                ui = st["ui"]
                names = {t["id"]: t["name"] for t in st["trends"]}
                bits = [f"view={ui['view']}"]
                if ui["sel"]:
                    bits.append(f"selected={names[ui['sel']]}")
                if ui["cmp"]:
                    bits.append("compare=" + ", ".join(names[i] for i in ui["cmp"]))
                if ui["board"]:
                    bits.append("board=" + ", ".join(names[i] for i in ui["board"]))
                if ui.get("hl"):
                    bits.append("highlighted=" + ", ".join(names[i] for i in ui["hl"]))
                f = {k: v for k, v in ui["f"].items() if v}
                if f:
                    bits.append(f"filters={f}")
                recs = {names[k]: len(v) for k, v in st["recs"].items()}
                if recs:
                    bits.append(f"recommendations={recs}")
                if st["note"]:
                    bits.append(f"note={st['note']!r}")
                out.append("  Canvas: " + "; ".join(bits) + f"  ({len(html) // 1024} KB page)")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text", help="what to say (for --action: the prompt)")
    ap.add_argument("--url", default="http://localhost:8080")
    ap.add_argument("--service", help="Cloud Run service name; resolves the stable URL and signs in")
    ap.add_argument("--action", help="send a canvas click with this action name")
    ap.add_argument("--ctx", default="{}", help="JSON context of the click (the canvas state)")
    ap.add_argument("--context", default=uuid.uuid4().hex, help="conversation id (contextId)")
    ap.add_argument("--raw", help="write the full JSON-RPC result to this file")
    args = ap.parse_args()

    headers: dict[str, str] = {}
    url = args.url.rstrip("/")
    if args.service:
        from cloud_run_url import stable_url

        url = stable_url(args.service)
    if url.startswith("https://"):
        tok = _id_token(url)
        if not tok:
            sys.exit("Could not mint an identity token: run `gcloud auth login` and retry.")
        headers["Authorization"] = f"Bearer {tok}"

    parts: list[dict] = [{"kind": "text", "text": args.text}]
    if args.action:
        ctx = {**json.loads(args.ctx), "prompt": args.text}
        parts.append({"kind": "data", "metadata": {"mimeType": A2UI}, "data": {
            "version": "v0.9", "action": {"name": args.action, "surfaceId": "cli", "sourceComponentId": "cli",
                                          "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "context": ctx}}})
    rpc = {"jsonrpc": "2.0", "id": uuid.uuid4().hex, "method": "message/send",
           "params": {"message": {"role": "user", "messageId": uuid.uuid4().hex, "contextId": args.context,
                                  "parts": parts}}}
    t0 = time.time()
    r = httpx.post(url + "/", json=rpc, headers=headers, timeout=180)
    r.raise_for_status()
    body = r.json()
    if "error" in body:
        sys.exit(f"A2A error: {body['error']}")
    result = body["result"]
    if args.raw:
        Path(args.raw).write_text(json.dumps(result, indent=2))

    final = (result.get("status") or {}).get("message") or {}
    all_parts = list(final.get("parts") or [])
    for art in result.get("artifacts") or []:
        all_parts += art.get("parts") or []
    texts = [p["text"] for p in all_parts if p.get("kind") == "text"]
    a2ui = [p["data"] for p in all_parts if (p.get("metadata") or {}).get("mimeType") == A2UI]
    chips = [q["question"] for p in all_parts if (p.get("metadata") or {}).get("mimeType") == SUGGEST
             for q in p["data"]["recommendedQuestionsResponse"]["suggestions"]]
    print(f"[{time.time() - t0:.1f}s] context={args.context} state={result['status']['state']}")
    print("Reply:", "\n       ".join(dict.fromkeys(texts)) or "(no text)")
    summary = canvas_summary(a2ui)
    print(summary or "  Canvas: (unchanged: no A2UI in this reply)")
    if chips:
        print("  Chips:", " | ".join(chips))
    return 0


if __name__ == "__main__":
    sys.exit(main())
