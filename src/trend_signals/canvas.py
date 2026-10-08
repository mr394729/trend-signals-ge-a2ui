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

"""Render the workspace into the Gemini Enterprise Canvas side panel.

The workspace is one IFrameSrcdoc inside a Canvas component (A2UI v0.9). The page is the built
single-file Vite bundle with the state spliced in; the iframe cannot fetch, so everything it shows
is in that state.
"""

from __future__ import annotations

from typing import Any

from trend_signals import catalog, state, ui_state
from trend_signals.kit import srcdoc
from trend_signals.kit.v09 import Surface

TITLE = "Trend Signals"
# Gemini Enterprise takes the frame height in pixels (there is no "fill the panel" option). The page is an app
# shell: header and tabs stay put and the content region scrolls, so it fills whatever the frame is. One fixed
# height fits a laptop-height Canvas; if the frame is a little taller than the panel, only the content region's
# bottom padding is cut off.
FRAME_HEIGHT = 1024


def chips_for(user: str) -> list[str]:
    """Follow-up chips under the chat reply: the questions worth asking about what the canvas shows."""
    ui = ui_state.get_ui(user)
    names = {t["id"]: t["name"] for t in catalog.dataset()["trends"]}
    if ui["view"] == "detail" and ui["sel"]:
        n = names.get(ui["sel"], "this trend")
        return [f"Which trend is most similar to {n}?", f"Is {n} worth a bigger buy?", "Recommend actions for this trend"]
    if ui["view"] == "compare":
        return ["Which one should I buy into first?", "Which has the better brand fit?", "Show my whitespace gaps"]
    if ui["view"] == "board":
        return ["Recommend actions for my board", "What am I missing?", "Which should I buy into first?"]
    if ui["view"] == "heatmap":
        return ["Which brand has the most whitespace?", "Which trend fits every brand?", "Where is Cymbal Active underserved?"]
    if ui["view"] == "timeline":
        return ["What peaks next?", "Which trends are about to fade?", "What should I buy for spring?"]
    return ["Where are my biggest whitespace gaps?", "Which trends are fading but heavily stocked?",
            "What should Cymbal Core buy into this season?"]


def render(user: str) -> tuple[list[dict[str, Any]], list[str]]:
    """(A2UI messages, suggestion chips) for the current canvas state of this user."""
    chips = chips_for(user)
    st = state.build(user, chips)
    html = srcdoc.render(st)
    if not html:
        raise RuntimeError("frontend bundle missing: run `npm run build` in frontend/ or set FRONTEND_DIST")
    s = Surface("trends-workspace")
    frame = s.iframe(html, TITLE, height=FRAME_HEIGHT)
    k = st["kpis"]
    s.canvas(title=TITLE,
             description=f"{k['tracked']} trends · {k['whitespace']} whitespace gaps · {k['at_risk']} at risk",
             icon="insights", child=frame)
    return s.messages(), chips


def open_text() -> str:
    k = state.kpis(catalog.dataset())
    return (f"The Trend Signals workspace is open next to this chat. It tracks {k['tracked']} trends: "
            f"{k['rising']} are accelerating, {k['whitespace']} show strong demand with thin assortment "
            f"coverage, and {k['at_risk']} are fading while heavily stocked. Click a trend to drill in, or "
            f"ask me. I can analyse, compare, recommend actions and update the workspace as we talk.")
