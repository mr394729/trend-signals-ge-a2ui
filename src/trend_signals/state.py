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

"""The injected canvas state: dataset + ui + agent-written content.

Contract with the iframe: `frontend/src/lib/trends.ts` (TrendsState). The
iframe cannot fetch (connect-src 'none'), so everything it renders is here.
"""

from __future__ import annotations

from typing import Any

from trend_signals import catalog, ui_state


def _opportunity(t: dict[str, Any]) -> int:
    return round(t["strength"] * (100 - t["coverage"]) / 100)


def kpis(ds: dict[str, Any]) -> dict[str, int]:
    ts = ds["trends"]
    return {
        "tracked": len(ts),
        "rising": sum(1 for t in ts if t["momentum"] >= 5),
        "whitespace": sum(1 for t in ts if t["strength"] >= 60 and t["coverage"] < 45),
        "at_risk": sum(1 for t in ts if t["life"] in ("mature", "decline") and t["coverage"] >= 65),
    }


def build(user: str, suggestions: list[str] | None = None) -> dict[str, Any]:
    ds = catalog.dataset()
    ui = ui_state.get_ui(user)
    return {
        "scene": "trends",
        **ds,
        "kpis": kpis(ds),
        "ui": ui,
        "recs": ui_state.get_recs(user),
        "note": ui_state.pop_note(user),
        "suggestions": suggestions or [],
    }
