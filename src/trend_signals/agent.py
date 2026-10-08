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

"""TrendAgent — an ADK agent with zero A2UI awareness: it analyses with tools and
drives the canvas through ui_state; the executor renders."""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from trend_signals.kit import config

from trend_signals import prompts
from trend_signals.kit import identity
from trend_signals.tools import TOOLS

APP_NAME = "trend_signals_agent"


def _instruction_provider(ctx: ReadonlyContext) -> str:
    return prompts.build_instruction(identity.key_from_state(ctx.state))


def build_runner() -> Runner:
    agent = LlmAgent(
        model=Gemini(model=config.MODEL),
        # One slow model call (seen: ~100 s) must not outlast the turn: time it out and retry.
        generate_content_config=types.GenerateContentConfig(http_options=types.HttpOptions(
            timeout=config.MODEL_CALL_TIMEOUT_MS, retry_options=types.HttpRetryOptions(attempts=3))),
        name=APP_NAME,
        description="Analyses fashion trend signals and drives the trend workspace canvas.",
        instruction=_instruction_provider,
        tools=TOOLS,
    )
    return Runner(app_name=APP_NAME, agent=agent, artifact_service=InMemoryArtifactService(),
                  session_service=InMemorySessionService(), memory_service=InMemoryMemoryService())
