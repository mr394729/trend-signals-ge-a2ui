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

import asyncio

import pytest
from a2a.server.events.event_queue import EventQueue
from a2a.types import DataPart, Message, Part, Role, TextPart

from trend_signals import executor, ui_state
from trend_signals.kit import srcdoc
from trend_signals.kit.emit import A2UI_MIME_TYPE, SUGGESTIONS_MIME_TYPE


def click(action: str, ctx: dict) -> Message:
    """A click as Gemini Enterprise sends it: the prompt text, then the v0.9 action data part."""
    return Message(message_id="m1", role=Role.user, parts=[
        Part(root=TextPart(text=ctx.get("prompt", "User action triggered."))),
        Part(root=DataPart(data={"version": "v0.9", "action": {
            "name": action, "surfaceId": "s1", "sourceComponentId": "c1",
            "timestamp": "2026-10-02T00:00:00Z", "context": ctx}},
            metadata={"mimeType": A2UI_MIME_TYPE}))])


def typed(text: str) -> Message:
    return Message(message_id="m2", role=Role.user, parts=[Part(root=TextPart(text=text))])


def text_of(m: Message) -> str:
    from trend_signals.kit.actions import extract_user_text

    return extract_user_text(m)


def test_a_canvas_action_is_read_with_its_prompt_and_state():
    m = click("ask", {"prompt": "Recommend actions for Barrel-leg denim", "view": "detail", "sel": "t02",
                      "cmp": "-", "board": "t04,t19", "metric": "tiktok", "ft": "-", "fb": "core", "fl": "-",
                      "fq": "-"})
    action, params, prompt = executor.read_click(m, text_of(m))
    assert action == "ask" and prompt == "Recommend actions for Barrel-leg denim"
    assert params["sel"] == "t02" and params["board"] == "t04,t19" and params["fb"] == "core"
    assert "prompt" not in params


def test_values_with_separators_survive_the_structured_context():
    m = click("ask", {"prompt": "Compare: a; b = c", "fq": "a;b=c"})
    _, params, prompt = executor.read_click(m, text_of(m))
    assert prompt == "Compare: a; b = c" and params["fq"] == "a;b=c"


def test_typed_text_is_not_a_click():
    m = typed("Where are my whitespace gaps?")
    assert executor.read_click(m, text_of(m)) is None


@pytest.mark.parametrize("text,expected", [
    ("hi", "open"), ("Open the workspace", "open"), ("", "open"), ("open trend signals", "open"),
    ("Where are my whitespace gaps?", "agent"), ("Recommend actions for Butter yellow", "agent"),
    ("Selected: ask; prompt=Compare these", "agent"), ("Selected: open", "open"),
])
def test_routing(text, expected):
    assert executor.route(text) == expected


def test_opening_the_workspace_replies_with_text_then_canvas_then_chips(user, monkeypatch):
    if not srcdoc.load_bundle():
        pytest.skip("frontend/dist is not built (make frontend-build)")
    monkeypatch.setattr(executor, "workspace_key", lambda *a, **k: user)
    ex = executor.TrendAgentExecutor()

    class Ctx:
        message = typed("hi")
        task_id, context_id, call_context = "task-1", "ctx-1", None

    async def run():
        q = EventQueue()
        await ex.execute(Ctx, q)
        events = []
        while not q.queue.empty():
            events.append(await q.dequeue_event())
        return events

    events = asyncio.run(run())
    final = events[-1]
    assert final.final and final.status.state.value == "completed"
    parts = final.status.message.parts
    assert isinstance(parts[0].root, TextPart) and "Trend Signals workspace is open" in parts[0].root.text
    mimes = [p.root.metadata.get("mimeType") for p in parts[1:]]
    assert mimes[-1] == SUGGESTIONS_MIME_TYPE and set(mimes[:-1]) == {A2UI_MIME_TYPE}


def test_an_action_updates_the_stored_canvas_state_before_the_agent_runs(user):
    m = click("ask", {"prompt": "x", "view": "compare", "cmp": "t01,t02", "board": "-", "sel": "-"})
    action, params, _ = executor.read_click(m, text_of(m))
    ui_state.remember_click(user, params)
    ui = ui_state.get_ui(user)
    assert ui["view"] == "compare" and ui["cmp"] == ["t01", "t02"] and ui["sel"] == ""


@pytest.mark.parametrize("text", ["Open the trend workspace", "open trend signals", "Show me the workspace",
                                  "launch the trend radar", "Open the workspace!", "please open the dashboard"])
def test_open_phrasings_are_deterministic(text):
    assert executor.route(text) == "open"


@pytest.mark.parametrize("text", ["Open the barrel-leg denim trend", "Show my whitespace gaps",
                                  "Start my board with the three best whitespace trends", "open"])
def test_other_requests_reach_the_agent(text):
    assert executor.route(text) == "agent" or text == "open"


def test_a_click_message_carries_the_workspace_state(user, monkeypatch):
    monkeypatch.setattr(executor, "workspace_key", lambda *a, **k: user)
    m = click("ask", {"prompt": "What is driving this trend?", "view": "detail", "sel": "t07", "board": "t04"})
    ui_state.remember_click(user, executor.read_click(m, text_of(m))[1])

    from a2a.server.agent_execution import RequestContext
    from a2a.types import MessageSendParams
    from google.adk.a2a.converters.part_converter import convert_a2a_part_to_genai_part

    ctx = RequestContext(request=MessageSendParams(message=m), task_id="t", context_id="c")
    req = executor._request_converter(ctx, convert_a2a_part_to_genai_part)
    text = req.new_message.parts[0].text
    assert text.startswith("What is driving this trend?")
    assert "selected trend: Chocolate brown" in text and "board: Butter yellow" in text


def test_a_slow_turn_is_cut_off_with_a_message(user, monkeypatch):
    from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor

    async def slow(self, context, queue):
        await asyncio.sleep(5)

    monkeypatch.setattr(A2aAgentExecutor, "execute", slow)
    monkeypatch.setattr(executor.config, "TURN_TIMEOUT_S", 0.2)
    monkeypatch.setattr(executor, "workspace_key", lambda *a, **k: user)
    ex = executor.TrendAgentExecutor()

    class Ctx:
        message = typed("Where are my whitespace gaps?")
        task_id, context_id, call_context = "task-2", "ctx-2", None

    async def run():
        q = EventQueue()
        await ex.execute(Ctx, q)
        return await q.dequeue_event()

    final = asyncio.run(run())
    assert final.final and "took longer than expected" in final.status.message.parts[0].root.text
