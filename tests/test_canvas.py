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

from trend_signals import canvas, ui_state
from trend_signals.kit import srcdoc


@pytest.fixture(autouse=True)
def _bundle():
    if not srcdoc.load_bundle():
        pytest.skip("frontend/dist is not built (make frontend-build)")


def test_canvas_messages_pass_the_catalog_validator(user):
    # Surface.messages validates against the Gemini Enterprise composite catalog and raises otherwise.
    messages, chips = canvas.render(user)
    kinds = [next(k for k in m if k != "version") for m in messages]
    assert kinds == ["createSurface", "updateComponents"]
    comps = {c["component"]: c for c in messages[1]["updateComponents"]["components"]}
    assert set(comps) == {"Canvas", "IFrameSrcdoc"}
    assert chips and all(len(c) <= 85 for c in chips)


def test_the_frame_carries_the_state_and_the_csp_meta(user):
    ui_state.get_ui(user)["view"] = "detail"
    ui_state.get_ui(user)["sel"] = "t02"
    messages, _ = canvas.render(user)
    html = next(c for c in messages[1]["updateComponents"]["components"]
                if c["component"] == "IFrameSrcdoc")["htmlContent"]
    assert "connect-src 'none'" in html
    assert "window.__TREND_SIGNALS_STATE__=" in html
    blob = html.split("window.__TREND_SIGNALS_STATE__=", 1)[1].split(";</script>", 1)[0]
    st = json.loads(blob.replace("<\\/", "</"))
    assert st["ui"]["view"] == "detail" and st["ui"]["sel"] == "t02"


def test_every_a2ui_part_is_under_the_1_mib_limit(user):
    messages, _ = canvas.render(user)
    assert all(len(json.dumps(m)) < 1_000_000 for m in messages)


def test_each_render_is_a_fresh_surface(user):
    a, _ = canvas.render(user)
    b, _ = canvas.render(user)
    assert a[0]["createSurface"]["surfaceId"] != b[0]["createSurface"]["surfaceId"]


def test_the_frame_has_the_fixed_app_shell_height(user):
    from trend_signals import canvas

    messages, _ = canvas.render(user)
    frame = next(c for c in messages[1]["updateComponents"]["components"] if c["component"] == "IFrameSrcdoc")
    assert frame["height"] == canvas.FRAME_HEIGHT == 1024


def test_state_text_cannot_end_the_script_or_open_a_comment():
    from trend_signals.kit import srcdoc as sd
    html = sd.inject_state("<html><head></head><body></body></html>",
                           {"note": "</script><!--<script>alert(1)</script>"})
    script = html.split("<script>", 1)[1].split("</script>", 1)[0]
    assert "<" not in script.split("=", 1)[1]
    assert json.loads(script.split("=", 1)[1].rstrip(";"))["note"].startswith("</script>")
