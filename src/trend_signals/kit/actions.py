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

"""Inbound click normalization.

Gemini Enterprise sends an A2UI v0.9 click as a Message with two parts:
  1. a TextPart with the button's ``context.prompt`` (or the generic
     ``"User action triggered."`` when the button has no prompt);
  2. a DataPart (``metadata.mimeType`` ``application/json+a2ui``) whose ``data``
     is ``{"version": "v0.9", "action": {name, surfaceId, sourceComponentId,
     timestamp, context}}``. Paths in ``context`` are resolved on the client.

Earlier formats are also accepted: the v0.8 ``{userAction: {...}}`` data part,
an A2UI-style context list of ``{key, value: {literalString|...}}`` entries,
an action embedded as JSON in a text part, and the v0.8 ``Selected: <name>; k=v``
text line. This module normalizes all of them to the canonical ``Selected:``
line so the deterministic click bridge routes every click identically; use
``extract_user_action`` for the context with its JSON types.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_DECOY_TEXT = "User action triggered."


def user_action_to_selected_text(user_action: dict) -> str:
    """Rebuild ``Selected: <name>; key=value; …`` from a structured userAction."""
    if not isinstance(user_action, dict):
        return ""
    name = user_action.get("name") or ""
    if not name:
        return ""
    ctx = user_action.get("context") or {}
    pairs: list[tuple[str, str]] = []
    if isinstance(ctx, dict):
        pairs = [(str(k), _flatten(v)) for k, v in ctx.items() if v is not None]
    elif isinstance(ctx, list):
        for entry in ctx:
            if not isinstance(entry, dict):
                continue
            k = entry.get("key")
            v = entry.get("value")
            if isinstance(v, dict):
                v = (
                    v.get("literalString")
                    if v.get("literalString") is not None
                    else v.get("literalNumber")
                    if v.get("literalNumber") is not None
                    else v.get("literalBoolean")
                )
            if k is not None and v is not None:
                pairs.append((str(k), _flatten(v)))
    kvs = "".join(f"; {k}={v}" for k, v in pairs)
    return f"Selected: {name}{kvs}"


def _flatten(v: Any) -> str:
    """Render a context value as a string (lists join with commas)."""
    if isinstance(v, (list, tuple)):
        return ",".join(str(x) for x in v)
    return str(v)


def extract_user_action(message: Any) -> dict | None:
    """Return the raw structured userAction dict from the message, if any.

    Prefer this over the flattened ``Selected:`` line when values may contain
    separators (newlines / semicolons / equals) — e.g. long form text fields.
    """
    for p in getattr(message, "parts", None) or []:
        root = getattr(p, "root", None)
        data = getattr(root, "data", None)
        if isinstance(data, dict):
            ua = data.get("userAction") or data.get("action")  # v0.8 | v0.9
            if isinstance(ua, dict):
                return ua
            if "name" in data and ("context" in data or "surfaceId" in data):
                return data
    return None


def _embedded_action(text: str) -> dict | None:
    """An action object embedded as JSON inside a text part, if any."""
    import json as _json

    i = text.find("{")
    if i < 0 or '"action"' not in text and '"userAction"' not in text:
        return None
    try:
        obj = _json.loads(text[i:])
    except ValueError:
        return None
    if isinstance(obj, dict):
        ua = obj.get("action") or obj.get("userAction")
        if isinstance(ua, dict) and ua.get("name"):
            return ua
    return None


def extract_user_text(message: Any) -> str:
    """The user's intent text for this turn.

    Precedence: structured userAction (rebuilt as a ``Selected:`` line) wins
    over free text; GE's decoy text part is dropped. Every inbound part shape
    is logged at INFO so this layer stays debuggable in Cloud Run logs.
    """
    if message is None:
        return ""
    parts = getattr(message, "parts", None) or []

    selected_lines: list[str] = []
    text_chunks: list[str] = []
    shapes: list[str] = []
    for p in parts:
        root = getattr(p, "root", None)
        kind = getattr(root, "kind", None) or type(root).__name__
        text = getattr(root, "text", None)
        data = getattr(root, "data", None)

        if isinstance(text, str) and text:
            shapes.append(f"text[{len(text)}b]")
            embedded = _embedded_action(text)
            if embedded:
                # GE's /a2a path flattens a click into ONE text part:
                # 'User action triggered. {"version":"v0.9","action":{…}}'
                line = user_action_to_selected_text(embedded)
                if line:
                    selected_lines.append(line)
            elif text.strip() != _DECOY_TEXT:
                text_chunks.append(text)
        elif isinstance(data, dict):
            shapes.append(f"data[keys={sorted(list(data.keys()))[:5]}]")
            err = data.get("error")
            if isinstance(err, dict):
                # Gemini Enterprise's renderer reported a problem ("Report to agent").
                logger.warning("[actions] client error: %s", err)
            # v0.8 sends {userAction: …}; v0.9 sends {version, action: …}
            ua = data.get("userAction") or data.get("action")
            if isinstance(ua, dict):
                line = user_action_to_selected_text(ua)
                if line:
                    selected_lines.append(line)
            elif "name" in data:
                line = user_action_to_selected_text(data)
                if line:
                    selected_lines.append(line)
        else:
            shapes.append(kind or "unknown")

    logger.info("[actions] inbound parts shapes=%s", shapes)
    if selected_lines:
        return selected_lines[0]
    return "\n".join(text_chunks)
