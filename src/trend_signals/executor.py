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

"""Executor: one A2A turn in, one reply out.

* Typed messages and canvas actions go to the ADK agent. Its tools analyse the data and change what
  the canvas shows (`ui_state`); the canvas itself is rendered here, after the model's reply.
* Opening the workspace (a greeting, or the `open` action) is deterministic and instant.

Canvas -> agent: the sealed iframe can only post an action to Gemini Enterprise. Every action carries
the canvas state (view, selected trend, comparison, board, filters) and a `prompt`, which becomes the
user's message. `ui_state.remember_click` stores the state; the agent's instruction reads it.
Agent -> canvas: tools call `ui_state`; when one asked for an update, the canvas is rendered with the
final reply and attached to the closing event (`final_panel`), where Gemini Enterprise shows it.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from a2a.server.agent_execution import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Message, Part, Role, TaskState, TaskStatus, TaskStatusUpdateEvent, TextPart
from google.adk.a2a.converters.event_converter import convert_event_to_a2a_events
from google.adk.a2a.converters.request_converter import (
    AgentRunRequest,
    convert_a2a_request_to_agent_run_request,
)
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor, A2aAgentExecutorConfig
from google.adk.agents.invocation_context import LlmCallsLimitExceededError, new_invocation_context_id
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.runners import Runner
from google.genai import types as genai_types

from trend_signals import canvas, catalog, ui_state
from trend_signals.agent import build_runner
from trend_signals.kit import config, final_panel
from trend_signals.kit.actions import _flatten, extract_user_action, extract_user_text
from trend_signals.kit.click_bridge import _kvs_to_dict, parse_click
from trend_signals.kit.emit import a2ui_parts, response_parts, suggestions_part
from trend_signals.kit.identity import SESSION_KEY, key_from_state, workspace_key

logger = logging.getLogger(__name__)

_GREETINGS = {"hi", "hey", "hello", "yo", "help", "start", ""}
# "Open the trend workspace", "show me the workspace", "launch trend signals", "open the radar" ...
_OPEN_RE = re.compile(r"^(please\s+)?(open|show|launch|start|go to)(\s+me)?(\s+(the|my))?(\s+trend)?(\s+signals)?"
                      r"(\s+(workspace|radar|dashboard|canvas|app))?$")


def read_click(message: Any, text: str) -> tuple[str, dict[str, str], str] | None:
    """(action, canvas params, prompt) for a click, or None for typed text.

    The structured action context is preferred over the flattened `Selected:` line: it keeps values
    that contain `;` or `=` intact.
    """
    click = parse_click(text)
    if click is None:
        return None
    action, params = click
    ctx = (extract_user_action(message) or {}).get("context")
    if isinstance(ctx, dict):
        prompt = str(ctx.get("prompt") or "").strip()
        params = {k: _flatten(v) for k, v in ctx.items() if k != "prompt"}
    else:
        prompt = _kvs_to_dict(text.split(";", 1)[1]).get("prompt", "").strip() if ";" in text else ""
    return action, params, prompt


def route(text: str) -> str:
    """'open' (deterministic) or 'agent'."""
    click = parse_click(text)
    if click is not None:
        return "open" if click[0] == "open" else "agent"
    t = (text or "").strip().lower().rstrip("!?. ")
    return "open" if t in _GREETINGS or t == "trend signals" or (_OPEN_RE.match(t) and len(t) > 4) else "agent"


class _CanvasInjector:
    """ADK's default event conversion. On the final model response it renders the canvas (only when a
    tool asked for an update) and stashes it for `final_panel.FinalPanelQueue`."""

    def __call__(self, event, invocation_context, task_id=None, context_id=None, part_converter_func=None):
        kwargs: dict[str, Any] = {}
        if part_converter_func is not None:
            kwargs["part_converter"] = part_converter_func
        a2a_events = convert_event_to_a2a_events(event, invocation_context, task_id, context_id, **kwargs)
        if not event.is_final_response():
            return a2a_events
        user = key_from_state(invocation_context.session.state)
        if not ui_state.take_update(user):
            return a2a_events
        try:
            messages, chips = canvas.render(user)
        except Exception:  # the reply still ships; the log says why the canvas did not
            logger.exception("[canvas] render failed")
            return a2a_events
        parts = a2ui_parts(messages) + [p for p in [suggestions_part(chips)] if p is not None]
        final_panel.stash(task_id, parts, None)
        logger.info("[canvas] ready (%d a2ui parts)", len(messages))
        return a2a_events


def _request_converter(context, part_converter):
    run_request = convert_a2a_request_to_agent_run_request(context, part_converter)
    if run_request.run_config is None:
        run_request.run_config = RunConfig(streaming_mode=StreamingMode.SSE, max_llm_calls=config.MAX_HOPS_PER_TURN)
    else:
        run_request.run_config.streaming_mode = StreamingMode.SSE
        run_request.run_config.max_llm_calls = config.MAX_HOPS_PER_TURN
    message = getattr(context, "message", None)
    click = read_click(message, extract_user_text(message))
    if click and click[2]:
        # The workspace state goes into the message itself: earlier turns of the conversation may be
        # about another trend, and "this trend" must mean the one the user has open now.
        user = workspace_key(context.context_id)
        names = {t["id"]: t["name"] for t in catalog.dataset()["trends"]}
        text = f"{click[2]}\n\n[Workspace right now: {ui_state.describe(user, names)}]"
        run_request.new_message = genai_types.Content(role="user", parts=[genai_types.Part(text=text)])
        logger.info("[request] canvas action %r -> %r", click[0], text[:160])
    return run_request


class TrendAgentExecutor(A2aAgentExecutor):
    def __init__(self) -> None:
        super().__init__(runner=build_runner(),
                         config=A2aAgentExecutorConfig(event_converter=_CanvasInjector(),
                                                       request_converter=_request_converter),
                         use_legacy=True)

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        message = getattr(context, "message", None)
        text = extract_user_text(message)
        user = workspace_key(context.context_id)
        click = read_click(message, text)
        if click is not None:
            ui_state.remember_click(user, click[1])
        if route(text) == "open":
            await self._open_turn(context, event_queue, user)
            return
        ui_state.take_update(user)  # drop anything left over from an earlier turn
        try:
            await asyncio.wait_for(
                super().execute(context, final_panel.FinalPanelQueue(event_queue, context.task_id)),  # type: ignore[arg-type]
                timeout=config.TURN_TIMEOUT_S)
        except asyncio.TimeoutError:
            logger.error("[executor] turn exceeded %.0f s", config.TURN_TIMEOUT_S)
            await self._final(context, event_queue, "That took longer than expected, so I stopped. "
                                                    "Please try again, or ask a narrower question.")
        except LlmCallsLimitExceededError:
            await self._final(context, event_queue, "That needed more analysis steps than I allow in one turn. "
                                                    "Could you ask a narrower question?")
        except Exception:
            logger.exception("[executor] agent turn failed")
            await self._final(context, event_queue, "I hit an error talking to the model, so I couldn't finish "
                                                    "that. The service logs have the cause; try again in a moment.")

    async def _open_turn(self, context, event_queue, user: str) -> None:
        try:
            messages, chips = canvas.render(user)
            parts = response_parts(canvas.open_text(), messages, chips)
        except Exception:
            logger.exception("[executor] open failed")
            parts = response_parts("I couldn't open the workspace: the canvas failed to render. "
                                   "The service logs have the cause.", None, [])
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.complete(message=updater.new_agent_message(parts=parts))

    async def _final(self, context, event_queue, text: str) -> None:
        await event_queue.enqueue_event(TaskStatusUpdateEvent(
            task_id=context.task_id, context_id=context.context_id, final=True,
            status=TaskStatus(state=TaskState.completed, message=Message(
                message_id=new_invocation_context_id(), role=Role.agent,
                parts=[Part(root=TextPart(text=text))]))))

    async def _prepare_session(self, context: RequestContext, run_request: AgentRunRequest, runner: Runner):
        session = await super()._prepare_session(context, run_request, runner)
        user = workspace_key(context.context_id)
        try:
            await runner.session_service.append_event(session, Event(
                invocation_id=new_invocation_context_id(), author="system",
                actions=EventActions(state_delta={SESSION_KEY: user})))
        except Exception:
            logger.exception("[executor] failed to stamp session state")
        return session
