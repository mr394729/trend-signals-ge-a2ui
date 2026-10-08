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

import pytest
from google.adk.tools import FunctionTool

from trend_signals import catalog, tools, ui_state


@pytest.mark.parametrize("fn", tools.TOOLS, ids=lambda f: f.__name__)
def test_every_tool_has_a_valid_function_declaration(fn):
    # ADK derives the model-facing schema from the signature and docstring; a type it cannot
    # express fails here instead of on the first live turn.
    decl = FunctionTool(fn)._get_declaration()
    assert decl.name == fn.__name__ and decl.description


def test_search_filters_and_sorts():
    out = tools.search_trends(type="color", lifecycle="growth", sort="opportunity")
    assert out["count"] >= 1
    assert all(t["type"] == "color" and t["lifecycle"] == "growth" for t in out["trends"])
    opp = [t["opportunity"] for t in out["trends"]]
    assert opp == sorted(opp, reverse=True)


def test_search_brand_adds_fit_and_sorts_by_it():
    out = tools.search_trends(brand="core", sort="fit", limit=3)
    fits = [t["brand_fit"] for t in out["trends"]]
    assert fits == sorted(fits, reverse=True) and len(fits) == 3


def test_get_trend_resolves_names_ids_and_fuzzy():
    assert tools.get_trend("t02")["name"] == "Barrel-leg denim"
    assert tools.get_trend("barrel-leg")["id"] == "t02"
    miss = tools.get_trend("nonexistent thing")
    assert "error" in miss and len(miss["tracked_trends"]) == 24


def test_get_trend_matched_products_are_real_skus():
    t = tools.get_trend("Quiet tailoring")
    assert t["matched_products"] and all(p["match_pct"] > 0 for p in t["matched_products"])


def test_compare_needs_two_known_trends():
    assert "error" in tools.compare_trends(["Barrel-leg denim"])
    out = tools.compare_trends(["Barrel-leg denim", "Butter yellow", "nope"])
    assert len(out["trends"]) == 2 and out["unmatched"] == ["nope"]


def test_scan_assortment_lists_gaps_and_risks():
    out = tools.scan_assortment()
    assert out["whitespace_opportunities"] and out["assortment_at_risk"]
    assert all(t["coverage_pct"] < 60 for t in out["whitespace_opportunities"])
    assert all(t["lifecycle"] in ("mature", "decline") for t in out["assortment_at_risk"])


def test_show_in_canvas_sets_state_and_requests_an_update(user, ctx):
    out = tools.show_in_canvas("detail", trend="Butter yellow", note="Opened it", tool_context=ctx)
    assert out["ok"]
    ui = ui_state.get_ui(user)
    assert ui["view"] == "detail" and ui["sel"] == "t04"
    assert ui_state.take_update(user) is True
    assert ui_state.take_update(user) is False  # consumed once
    assert ui_state.pop_note(user) == "Opened it"


def test_show_in_canvas_validates(user, ctx):
    assert "error" in tools.show_in_canvas("sideways", tool_context=ctx)
    assert "error" in tools.show_in_canvas("detail", trend="zzz", tool_context=ctx)
    assert "error" in tools.show_in_canvas("compare", compare=["Butter yellow"], tool_context=ctx)
    tools.show_in_canvas("compare", compare=["Butter yellow", "Barrel-leg denim"], tool_context=ctx)
    assert ui_state.get_ui(user)["cmp"] == ["t04", "t02"]


def test_show_in_canvas_applies_filters_for_map(user, ctx):
    tools.show_in_canvas("map", type="Color", lifecycle="Growth", brand="Cymbal Studio", tool_context=ctx)
    assert ui_state.get_ui(user)["f"] == {"type": "color", "brand": "studio", "life": "growth", "q": ""}


def test_update_board_adds_removes_and_reports_unknowns(user, ctx):
    out = tools.update_board(add=["Butter yellow", "Barrel-leg denim", "nope"], tool_context=ctx)
    assert out["board"] == ["Butter yellow", "Barrel-leg denim"] and out["unmatched"] == ["nope"]
    out = tools.update_board(remove=["Butter yellow"], tool_context=ctx)
    assert out["board"] == ["Barrel-leg denim"]


def test_save_recommendations_validates_the_format(user, ctx):
    good = "high | Buyer | next 2 weeks | Add two SKUs | Coverage is 31%"
    out = tools.save_recommendations("Barrel-leg denim", [good], tool_context=ctx)
    assert out["saved"] == 1
    rec = ui_state.get_recs(user)["t02"][0]
    assert rec == {"priority": "high", "owner": "Buyer", "timing": "next 2 weeks",
                   "action": "Add two SKUs", "why": "Coverage is 31%"}
    ui = ui_state.get_ui(user)
    assert ui["view"] == "detail" and ui["sel"] == "t02"
    bad = tools.save_recommendations("Barrel-leg denim", ["urgent | a | b | c | d", "just words"], tool_context=ctx)
    assert "error" in bad and len(bad["rejected"]) == 2


def test_resolve_prefers_exact_over_fuzzy():
    assert catalog.resolve("Cherry red")["id"] == "t05"
    assert catalog.resolve("") is None


@pytest.mark.parametrize("view", ["heatmap", "timeline"])
def test_the_new_views_can_be_opened_by_the_agent(user, ctx, view):
    assert tools.show_in_canvas(view, highlight=["Butter yellow"], tool_context=ctx)["ok"]
    ui = ui_state.get_ui(user)
    assert ui["view"] == view and ui["hl"] == ["t04"]


def test_tool_arguments_are_bounded(user, ctx):
    long = "x" * 5000
    assert tools.search_trends(limit="many")["count"] >= 1   # a bad limit falls back to the default
    assert len(tools.search_trends(limit="many")["trends"]) == 8
    action = f"high | {long} | next 2 weeks | {long} | {long}"
    assert tools.save_recommendations("Barrel-leg denim", [action, action], tool_context=ctx)["saved"] == 2
    rec = next(iter(ui_state.get_recs(user).values()))[0]
    assert max(len(rec[k]) for k in ("owner", "action", "why")) <= tools.MAX_TEXT
    tools.show_in_canvas("map", query=long, tool_context=ctx)
    assert len(ui_state.get_ui(user)["f"]["q"]) <= 80
    out = tools.update_board(add=[long] * 1000, tool_context=ctx)
    assert len(out["unmatched"]) == tools.MAX_REFS and all(len(r) <= 80 for r in out["unmatched"])
