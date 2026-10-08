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

"""WebFrameSrcdoc HTML assembly — bundle load + state injection.

Invariants:
* The built single-file Vite bundle is self-contained and carries a CSP meta
  ``connect-src 'none'`` (injected at build time by the geSrcdocCsp plugin), which
  keeps it offline when opened directly; Gemini Enterprise removes the meta element
  and applies its own policy (no network, inline scripts and styles only).
* State is spliced as ``<script>window.__TREND_SIGNALS_STATE__ = {...}</script>``
  before ``</head>``; every ``<`` in the JSON is escaped to ``\\u003c`` so no string
  value (``</script>``, ``<!--``) can end the script or change how the HTML parser reads it.
* No fetch happens inside the iframe — ALL data must be in the injected state.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from trend_signals.kit import config

logger = logging.getLogger(__name__)

WINDOW_KEY = "__TREND_SIGNALS_STATE__"

_bundle_cache: str | None = None


def _bundle_path() -> Path:
    primary = Path(config.FRONTEND_DIST) / "index.html"
    if primary.exists():
        return primary
    # repo-root fallback for local dev (uv run from the workspace root)
    return Path(__file__).resolve().parents[3] / "frontend" / "dist" / "index.html"


def load_bundle() -> str:
    """Memoized read of the single-file bundle; "" (logged) when missing."""
    global _bundle_cache
    if _bundle_cache is not None:
        return _bundle_cache
    path = _bundle_path()
    try:
        _bundle_cache = path.read_text(encoding="utf-8")
        logger.info("[srcdoc] loaded bundle %s (%d bytes)", path, len(_bundle_cache))
    except FileNotFoundError:
        logger.error(
            "[srcdoc] bundle not found at %s — run `make frontend-build` or set FRONTEND_DIST",
            path,
        )
        _bundle_cache = ""
    return _bundle_cache


def inject_state(html: str, state: dict) -> str:
    """Splice the state script before ``</head>`` (fallback: <body>, prepend)."""
    payload = json.dumps(state, ensure_ascii=False, default=str).replace("<", "\\u003c")
    script = f"<script>window.{WINDOW_KEY}={payload};</script>"
    for needle in ("</head>", "<body>"):
        idx = html.find(needle)
        if idx != -1:
            return html[:idx] + script + html[idx:]
    return script + html


def render(state: dict) -> str:
    """Full ``htmlContent`` for a WebFrameSrcdoc ("" if the bundle is missing)."""
    html = load_bundle()
    if not html:
        return ""
    return inject_state(html, state)
