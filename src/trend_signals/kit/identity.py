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

"""Which workspace a turn belongs to.

Workspace state is keyed by the A2A conversation (``contextId``). Gemini Enterprise keeps one ``contextId`` per
conversation, so each conversation has its own workspace, and one user's conversation cannot read or change
another's.

Message metadata is not used for identity: the caller sets it, so a user id found there proves nothing. To keep
state per user across conversations (for example a shortlist), resolve the user from a verified credential, such as
an OAuth access token from a Gemini Enterprise authorization validated on the server, and key the state by that.
"""

from __future__ import annotations

import hashlib
from typing import Any

# Key under which the executor stamps the workspace key into the ADK session state, so tools and the
# instruction provider can read it.
SESSION_KEY = "workspace_key"


def workspace_key(context_id: str | None) -> str:
    """The workspace key for an A2A conversation."""
    if not context_id:
        raise ValueError("the A2A request has no contextId, so there is no conversation to key the workspace by")
    return "c_" + hashlib.sha256(context_id.encode()).hexdigest()[:16]


def key_from_state(state: Any) -> str:
    """The workspace key the executor stamped into the session state."""
    key = (state or {}).get(SESSION_KEY) if isinstance(state, dict) or hasattr(state, "get") else None
    if not key:
        raise RuntimeError(f"the session state has no {SESSION_KEY!r}: the executor stamps it in _prepare_session; "
                           "check the log for 'failed to stamp session state'")
    return str(key)
