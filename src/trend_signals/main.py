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

"""A2A server for the Trend Signals agent."""

from __future__ import annotations

import logging

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from starlette.responses import JSONResponse
from starlette.routing import Route

from trend_signals.card import build_agent_card
from trend_signals.executor import TrendAgentExecutor
from trend_signals.kit import config

logging.basicConfig(level=logging.INFO)
config.require_project()

handler = DefaultRequestHandler(agent_executor=TrendAgentExecutor(), task_store=InMemoryTaskStore())
app = A2AStarletteApplication(agent_card=build_agent_card(), http_handler=handler).build()


async def health(_request):
    return JSONResponse({"status": "ok", "service": "trend-signals"})


app.routes.append(Route("/health", health, methods=["GET"]))
