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

import json

import pytest

from trend_signals import catalog, state, ui_state


def test_dataset_is_deterministic_and_shaped():
    ds = catalog.dataset()
    assert len(ds["trends"]) == 24
    assert ds["weeks"][ds["hist"] - 1] == ds["as_of"]
    for t in ds["trends"]:
        assert len(t["series"]["overall"]) == ds["hist"] + ds["fc"]
        assert len(t["band"]) == ds["fc"]
        assert set(t["fit"]) == {b["id"] for b in ds["brands"]}
        assert 0 <= t["strength"] <= 100 and 0 <= t["coverage"] <= 100
        for m in t["products"]:
            assert m["sku"] in ds["products"]


def test_kpis_match_the_definitions_the_ui_uses():
    ds = catalog.dataset()
    k = state.kpis(ds)
    assert k["tracked"] == 24
    assert k["whitespace"] == sum(1 for t in ds["trends"] if t["strength"] >= 60 and t["coverage"] < 45)
    assert k["at_risk"] == sum(1 for t in ds["trends"] if t["life"] in ("mature", "decline") and t["coverage"] >= 65)


def test_build_carries_ui_recs_and_a_one_shot_note(user):
    ui_state.set_note(user, "Highlighted the gaps")
    first = state.build(user, ["a"])
    assert first["scene"] == "trends" and first["note"] == "Highlighted the gaps"
    assert first["suggestions"] == ["a"]
    assert state.build(user)["note"] == ""  # shown once


def test_state_fits_one_a2ui_data_part():
    # Gemini Enterprise caps one A2UI DataPart at 1 MiB; the state is spliced into the page inside it.
    assert len(json.dumps(state.build("size-check"))) < 200_000


def test_remember_click_adopts_canvas_state(user):
    ui_state.remember_click(user, {"view": "detail", "sel": "t02", "cmp": "t01,t04", "board": "-",
                                   "metric": "tiktok", "ft": "color", "fb": "-", "fl": "growth", "fq": "-"})
    ui = ui_state.get_ui(user)
    assert ui["view"] == "detail" and ui["sel"] == "t02" and ui["cmp"] == ["t01", "t04"]
    assert ui["board"] == [] and ui["metric"] == "tiktok"
    assert ui["f"] == {"type": "color", "brand": "", "life": "growth", "q": ""}


def test_remember_click_ignores_unknown_values(user):
    ui_state.remember_click(user, {"view": "bogus", "metric": "bogus"})
    ui = ui_state.get_ui(user)
    assert ui["view"] == "map" and ui["metric"] == "overall"


def test_workspaces_are_keyed_by_conversation_not_by_caller_metadata():
    from trend_signals.kit import identity
    a, b = identity.workspace_key("ctx-a"), identity.workspace_key("ctx-b")
    assert a != b and a == identity.workspace_key("ctx-a")
    with pytest.raises(ValueError):
        identity.workspace_key("")
    with pytest.raises(RuntimeError):
        identity.key_from_state({})


def test_click_state_and_workspace_count_are_bounded(monkeypatch):
    monkeypatch.setattr(ui_state, "MAX_WORKSPACES", 3)
    for n in range(5):
        ui_state.get_ui(f"bound-{n}")
    assert "bound-0" not in ui_state._ui and "bound-4" in ui_state._ui and len(ui_state._ui) <= 3
    ui_state.remember_click("bound-4", {"board": ",".join(["x" * 500] * 1000), "fq": "q" * 5000, "sy": "9" * 50})
    ui = ui_state.get_ui("bound-4")
    assert len(ui["board"]) == 24 and all(len(i) <= 16 for i in ui["board"])
    assert len(ui["f"]["q"]) <= 80 and ui["sy"] <= 10**8
