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

"""Deterministic click-bridge parser.

Clicks — whether they arrive as structured userActions (normalized by
``actions.extract_user_text``) or GE-flattened text — look like:

    Selected: <action>; key=value; key=value; ...

``parse_click`` translates that into ``(action, params)``. Routing action →
handler/bundle is per-agent (each agent owns its own routing table); the LLM is
never involved in the click path.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_CLICK_BRIDGE_RE = re.compile(r"^Selected:\s*([A-Za-z][A-Za-z0-9_]*)\s*(?:;\s*(.*))?$")

# Informational-only params forwarded by frontends (current scene, history) —
# context for resolvers, never state-builder inputs.
META_PARAM_KEYS = {"_scene", "_history", "prompt"}  # prompt = GE bubble text


def _kvs_to_dict(kvs: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for piece in kvs.split(";"):
        if "=" not in piece:
            continue
        key, val = piece.split("=", 1)
        key = key.strip()
        if not key:
            continue
        out[key] = val.strip()
    return out


def parse_click(text: str) -> tuple[str, dict[str, str]] | None:
    """Return ``(action, params)`` for a click-bridge line, else None.

    Strips META_PARAM_KEYS (logged at INFO). None ⇒ not a click; the caller
    falls through to its free-text path.
    """
    if not text:
        return None
    m = _CLICK_BRIDGE_RE.match(text.strip())
    if not m:
        return None
    action, kvs = m.group(1), m.group(2) or ""
    raw = _kvs_to_dict(kvs)
    meta = {k: v for k, v in raw.items() if k in META_PARAM_KEYS}
    params = {k: v for k, v in raw.items() if k not in META_PARAM_KEYS}
    logger.info(
        "[click_bridge] action=%s params=%s scene=%r history=%r",
        action, params, meta.get("_scene"), meta.get("_history"),
    )
    return action, params
