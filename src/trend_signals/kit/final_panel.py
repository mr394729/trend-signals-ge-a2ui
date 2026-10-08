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

"""Attach the turn's card to the event Gemini Enterprise shows as the answer.

ADK's A2A executor streams the model's final response as a `working` status update before it sends the
closing artifact and the `completed` status. Gemini Enterprise turns `working` messages into collapsed
"Show thinking" content, so a card attached there is hidden. The event converter therefore only
stashes the card; this queue wrapper attaches it once, to the closing artifact or, if there is none,
to the final `completed` status message.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from a2a.types import (
    DataPart,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
)

from trend_signals.kit.emit import A2UI_MIME_TYPE, SUGGESTIONS_MIME_TYPE

logger = logging.getLogger(__name__)

# task_id -> (parts to attach, metadata to merge into the final event)
_PENDING: dict[str, tuple[list[Part], dict[str, Any]]] = {}


def stash(task_id: str | None, parts: list[Part], metadata: dict[str, Any] | None = None) -> None:
    """Keep the turn's card for the final event (the first stash per task wins)."""
    if not task_id or task_id in _PENDING:
        return
    _PENDING[task_id] = (parts, metadata or {})
    while len(_PENDING) > 512:
        _PENDING.pop(next(iter(_PENDING)))


def _ui_part(p: Part) -> bool:
    root = getattr(p, "root", None)
    md = getattr(root, "metadata", None) or {}
    return isinstance(root, DataPart) and md.get("mimeType") in (A2UI_MIME_TYPE, SUGGESTIONS_MIME_TYPE)


class FinalPanelQueue:
    """EventQueue proxy that delivers the stashed card with the answer, exactly once."""

    def __init__(self, inner: Any, task_id: str | None) -> None:
        self._inner = inner
        self._task_id = task_id
        self._seen: set[str] = set()

    def _dedup(self, parts):
        out = []
        for p in parts or []:
            if _ui_part(p):
                key = json.dumps(p.root.data, sort_keys=True, default=str)
                if key in self._seen:
                    continue
                self._seen.add(key)
            out.append(p)
        return out

    def _take(self):
        return _PENDING.pop(self._task_id, None) if self._task_id else None

    async def enqueue_event(self, event) -> None:
        pending = None
        if isinstance(event, TaskArtifactUpdateEvent) and event.last_chunk is not False:
            pending = self._take()
            if pending:
                event.artifact.parts = list(event.artifact.parts or []) + pending[0]
        elif isinstance(event, TaskStatusUpdateEvent) and event.final:
            pending = self._take()
            if pending:
                msg = event.status.message
                if msg is None:
                    from google.adk.agents.invocation_context import new_invocation_context_id

                    event.status.message = Message(message_id=new_invocation_context_id(),
                                                   role=Role.agent, parts=list(pending[0]))
                else:
                    msg.parts = list(msg.parts or []) + pending[0]
        if pending:
            if pending[1]:
                event.metadata = {**(event.metadata or {}), **pending[1]}
            logger.info("[final_panel] card attached to %s", type(event).__name__)
        msg = getattr(getattr(event, "status", None), "message", None)
        if msg is not None:
            msg.parts = self._dedup(msg.parts)
        art = getattr(event, "artifact", None)
        if art is not None:
            art.parts = self._dedup(art.parts)
        await self._inner.enqueue_event(event)

    def __getattr__(self, name):
        return getattr(self._inner, name)
