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

"""Render the workspace views from the PRODUCTION bundle, exactly as the agent injects it.

    make screenshots        # needs: uv run playwright install chromium

Writes docs/images/<view>-<width>.png. The state is `trend_signals.state.build`, spliced the same
way `kit.srcdoc.inject_state` does it, so these frames show the real page, not a design mock.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from trend_signals import state, ui_state
from trend_signals.kit import srcdoc

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "images"

RECS = [
    "high | Women's buyer | next 2 weeks | Add two barrel-leg SKUs to the Core Q1 buy | Coverage is 31% against a strength of 74",
    "medium | Design lead | this month | Brief a recycled-content rigid wash | Fabric and fit signals both rise on search",
    "low | Marketing | next quarter | Plan creator seeding for the launch | TikTok leads the other channels by about three weeks",
]


def scenario(name: str) -> dict:
    user = f"shot-{name}"
    ui = ui_state.get_ui(user)
    ui["board"] = ["t02", "t04", "t19"]
    if name == "detail":
        ui["view"], ui["sel"] = "detail", "t02"
        from trend_signals import tools

        tools.save_recommendations("Barrel-leg denim", RECS, tool_context=_Ctx(user))
    elif name == "compare":
        ui["view"], ui["cmp"] = "compare", ["t02", "t16", "t04"]
    elif name == "board":
        ui["view"] = "board"
    elif name == "list":
        ui["view"] = "list"
    elif name in ("heatmap", "timeline"):
        ui["view"] = name
    elif name == "dark":
        ui["view"], ui["sel"] = "detail", "t04"
    elif name == "palette":
        ui["view"] = "map"
    elif name == "highlight":
        ui["view"], ui["hl"] = "map", ["t04", "t12", "t02", "t07", "t19"]
    st = state.build(user)
    if name == "highlight":
        st["note"] = "Highlighted the five biggest whitespace gaps: strong demand, thin coverage."
    return copy.deepcopy(st)


class _Ctx:
    def __init__(self, user: str) -> None:
        from trend_signals.kit import identity

        self.state = {identity.SESSION_KEY: user}


def main() -> int:
    bundle = srcdoc.load_bundle()
    if not bundle:
        print("frontend/dist is missing: run `make frontend-build` first", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    only = sys.argv[1:] or ["map", "highlight", "list", "detail", "compare", "board", "heatmap", "timeline", "dark", "palette"]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width in (1000, 520):
            for name in only:
                page = browser.new_page(viewport={"width": width, "height": 2700 if name in ("detail", "list", "dark") else 1024})
                html = srcdoc.inject_state(bundle, scenario(name))
                page.set_content(html)
                page.wait_for_timeout(2600)  # let the entrance animations finish
                if name == "dark":
                    page.click('button[aria-label="Switch to the dark theme"]')
                    page.wait_for_timeout(1800)
                if name == "palette":
                    page.keyboard.press("Control+k")
                    page.keyboard.type("den")
                    page.wait_for_timeout(500)
                path = OUT / f"{name}-{width}.png"
                page.screenshot(path=str(path))
                print("wrote", path.relative_to(ROOT))
                page.close()
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
