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

"""What the canvas shows, per conversation (see kit/identity.py), plus what the agent has written into it.

The iframe is sealed (it cannot call the agent), so the contract is:
  * canvas -> agent: every action posts the canvas state as click params
    (view, selected trend, comparison, board, filters); `remember_click` stores it.
  * agent -> canvas: tools change this state (`show_in_canvas`, `update_board`,
    `save_recommendations`); the executor re-renders the canvas from it after
    the model's reply.
Single-writer per conversation per turn — the Gemini Enterprise conversation model.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

VIEWS = ("map", "list", "heatmap", "timeline", "detail", "compare", "board")
METRICS = ("overall", "tiktok", "pinterest", "search", "editorial", "runway")

_DEFAULT_UI: dict[str, Any] = {
    "view": "map", "sel": "", "cmp": [], "board": [], "metric": "overall", "hl": [], "sy": 0,
    "f": {"type": "", "brand": "", "life": "", "q": ""},
}
_ui: dict[str, dict[str, Any]] = {}
_recs: dict[str, dict[str, list[dict[str, str]]]] = {}
_notes: dict[str, dict[str, Any]] = {}
_dirty: dict[str, float] = {}  # user -> time the agent last asked for a canvas update
_FRESH_S = 180.0
# State is in memory, one entry per conversation: keep the most recent MAX_WORKSPACES, and bound what a click
# (which the caller controls) can store.
MAX_WORKSPACES = 500
_MAX_IDS, _MAX_ID, _MAX_FIELD = 24, 16, 80


def get_ui(user: str) -> dict[str, Any]:
    cur = _ui.get(user)
    if cur is None:
        while len(_ui) >= MAX_WORKSPACES:   # dicts keep insertion order: drop the oldest workspace
            _forget(next(iter(_ui)))
        cur = {**_DEFAULT_UI, "cmp": [], "board": [], "hl": [], "f": dict(_DEFAULT_UI["f"])}
        _ui[user] = cur
    return cur


def _forget(user: str) -> None:
    for store in (_ui, _recs, _notes, _dirty):
        store.pop(user, None)


def _csv(v: str | None) -> list[str]:
    return [x[:_MAX_ID] for x in (v or "").split(",") if x and x != "-"][:_MAX_IDS]


def remember_click(user: str, params: dict[str, str]) -> None:
    """Adopt the canvas state the iframe sent with an action."""
    ui = get_ui(user)
    if params.get("view") in VIEWS:
        ui["view"] = params["view"]
    if "sel" in params:
        ui["sel"] = "" if params["sel"] == "-" else params["sel"][:_MAX_ID]
    if "cmp" in params:
        ui["cmp"] = _csv(params["cmp"])
    if "board" in params:
        ui["board"] = _csv(params["board"])
    if "hl" in params:
        ui["hl"] = _csv(params["hl"])
    if params.get("sy", "").isdigit():
        ui["sy"] = min(int(params["sy"][:9]), 10**8)
    if params.get("metric") in METRICS:
        ui["metric"] = params["metric"]
    for k, pk in (("type", "ft"), ("brand", "fb"), ("life", "fl"), ("q", "fq")):
        if pk in params:
            ui["f"][k] = "" if params[pk] == "-" else params[pk][:_MAX_FIELD]
    logger.info("[ui] %s <- canvas %s", user, ui)


def request_update(user: str) -> None:
    _dirty[user] = time.time()


def take_update(user: str) -> bool:
    t = _dirty.pop(user, 0.0)
    return bool(t) and time.time() - t <= _FRESH_S


def get_recs(user: str) -> dict[str, list[dict[str, str]]]:
    return _recs.setdefault(user, {})


def set_note(user: str, text: str) -> None:
    _notes[user] = {"text": text, "ts": time.time()}


def pop_note(user: str) -> str:
    n = _notes.pop(user, None)
    return n["text"] if n and time.time() - n["ts"] <= _FRESH_S else ""


def describe(user: str, names: dict[str, str]) -> str:
    """One paragraph for the agent's instruction: what the user is looking at."""
    ui = get_ui(user)
    f = {k: v for k, v in ui["f"].items() if v}
    parts = [f"view={ui['view']}"]
    if ui["sel"]:
        parts.append(f"selected trend: {names.get(ui['sel'], ui['sel'])} ({ui['sel']})")
    if ui["cmp"]:
        parts.append("comparing: " + ", ".join(names.get(c, c) for c in ui["cmp"]))
    if ui["board"]:
        parts.append("board: " + ", ".join(names.get(c, c) for c in ui["board"]))
    if ui["hl"]:
        parts.append("highlighted on the map: " + ", ".join(names.get(c, c) for c in ui["hl"]))
    if f:
        parts.append("filters: " + ", ".join(f"{k}={v}" for k, v in f.items()))
    return "; ".join(parts)
