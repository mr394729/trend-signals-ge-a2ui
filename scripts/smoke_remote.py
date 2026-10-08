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

"""Remote smoke: agent card + one message/send against a deployed service.

    uv run python scripts/smoke_remote.py trend-signals-agent   # service name
    uv run python scripts/smoke_remote.py https://<the service's URL>

A service name is resolved to its stable URL (scripts/cloud_run_url.py, needs
GOOGLE_CLOUD_PROJECT and REGION). Private Cloud Run: mints an identity token
with your active gcloud account.
Asserts: card serves, a2ui DataParts present, parts order sane.
"""

from __future__ import annotations

import subprocess
import sys
import uuid

import httpx

A2UI_MIME = "application/json+a2ui"


def _id_token(audience: str) -> str | None:
    # --audiences works only for service accounts; user accounts mint a token
    # with gcloud's own client-id audience, which Cloud Run accepts for IAM'd
    # callers. Try the SA form first, fall back to the plain user-account form.
    for args in (
        ["gcloud", "auth", "print-identity-token", f"--audiences={audience}"],
        ["gcloud", "auth", "print-identity-token"],
    ):
        try:
            tok = subprocess.check_output(
                args, text=True, stderr=subprocess.DEVNULL
            ).strip()
            if tok:
                return tok
        except Exception:
            continue
    return None


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    base = sys.argv[1].rstrip("/")
    if not base.startswith("https://"):
        from cloud_run_url import stable_url

        base = stable_url(base)
    headers = {}
    tok = _id_token(base)
    if not tok:
        sys.exit("Could not mint an identity token: run `gcloud auth login` and retry.")
    if tok:
        headers["Authorization"] = f"Bearer {tok}"

    card = httpx.get(f"{base}/.well-known/agent-card.json", headers=headers,
                     timeout=30)
    card.raise_for_status()
    cj = card.json()
    exts = [e.get("uri") for e in (cj.get("capabilities") or {}).get("extensions", [])]
    print(f"card OK: {cj.get('name')} url={cj.get('url')} extensions={exts}")
    assert cj.get("url", "").startswith("https://"), "card url must be the stable host"

    rpc = {
        "jsonrpc": "2.0", "id": "smoke", "method": "message/send",
        "params": {"message": {"role": "user", "messageId": uuid.uuid4().hex,
                                "contextId": uuid.uuid4().hex,
                                "parts": [{"kind": "text", "text": "hello"}]}},
    }
    r = httpx.post(base + "/", json=rpc, headers=headers, timeout=60)
    r.raise_for_status()
    body = r.json()
    assert "error" not in body, body.get("error")
    result = body.get("result") or {}
    parts = ((result.get("status") or {}).get("message") or {}).get("parts") or []
    for h in result.get("history") or []:
        if h.get("role") == "agent":
            parts += h.get("parts") or []
    mimes = [((p.get("metadata") or {}).get("mimeType")) or
             ("text" if "text" in p else "data") for p in parts]
    print(f"message/send OK: {len(parts)} parts, mimes={mimes}")
    assert A2UI_MIME in mimes, "no a2ui part in response"
    print("SMOKE PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
