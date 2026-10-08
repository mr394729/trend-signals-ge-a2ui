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

"""A2A part assembly for A2UI responses.

The wire contract (proven on Gemini Enterprise):

* Every A2UI message rides in its own ``DataPart`` with
  ``metadata.mimeType == "application/json+a2ui"``.
* Follow-up suggestion chips ride in ONE ``DataPart`` with
  ``metadata.mimeType == "application/json+suggestions"`` and payload
  ``{"recommendedQuestionsResponse": {"suggestions": [{"question": ...}],
  "questions": [...]}}``. The GE UI reads ``recommendedQuestionsResponse.suggestions``
  (with "ed"); GE's own assistant sends ``questions``, so both are sent. The
  backend also accepts ``recommendQuestionsResponse`` but the UI ignores it.
* Part ORDER matters: TextPart (chat line) first, then the A2UI DataParts,
  then the suggestions DataPart last.
* A card's ``surfaceId`` is fresh every turn (uuid suffix), so each card is its
  own surface; a ``createSurface`` for an existing id resets that surface. The Canvas
  panel is also created fresh each turn, which reopens it with the current state.
"""

from __future__ import annotations

import uuid
from typing import Any

from a2a.types import DataPart, Part, TextPart

A2UI_MIME_TYPE = "application/json+a2ui"
SUGGESTIONS_MIME_TYPE = "application/json+suggestions"


def fresh_surface_id(prefix: str) -> str:
    """A per-turn surface id: ``<prefix>-<8 hex chars>``."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def a2ui_parts(messages: list[dict[str, Any]]) -> list[Part]:
    """One A2UI DataPart per message (the SDK's create_a2ui_part)."""
    from trend_signals.kit import sdk

    return sdk.parts(messages)


def suggestions_part(questions: list[str]) -> Part | None:
    """The GE follow-up chips part, or None when there is nothing to suggest."""
    qs = [q for q in (questions or []) if q][:3]  # GE agents cap at 3 chips, <= 85 chars
    if not qs:
        return None
    return Part(
        root=DataPart(
            # "suggestions" is what the Gemini Enterprise UI reads; Gemini Enterprise's
            # own assistant sends "questions". Both keys carry the same chips.
            data={"recommendedQuestionsResponse": {
                "suggestions": [{"question": q[:85],
                                 "FollowUpQuestionMetadata": {"sourceType": "A2A_AGENT"}} for q in qs],
                "questions": [q[:85] for q in qs]}},
            metadata={"mimeType": SUGGESTIONS_MIME_TYPE},
        )
    )


def response_parts(
    text: str | None,
    a2ui_messages: list[dict[str, Any]] | None = None,
    suggestions: list[str] | None = None,
) -> list[Part]:
    """Assemble a full response ``parts`` list in the load-bearing order."""
    parts: list[Part] = []
    if text:
        parts.append(Part(root=TextPart(text=text)))
    if a2ui_messages:
        parts.extend(a2ui_parts(a2ui_messages))
    sp = suggestions_part(suggestions or [])
    if sp is not None:
        parts.append(sp)
    return parts
