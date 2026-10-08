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

"""The agent card: what Gemini Enterprise is told about this agent (also used by registration)."""

from __future__ import annotations

from a2a.types import AgentCapabilities, AgentCard, AgentExtension, AgentSkill

from trend_signals.kit import config, v09

DISPLAY_NAME = "Trend Signals"
DESCRIPTION = ("A trend-analytics workspace: an interactive opportunity map, trend drill-downs and a "
               "shortlist board in a side panel, driven by an analyst agent you can ask for "
               "comparisons, whitespace gaps and recommended actions.")
STARTER_PROMPTS = ["Open the trend workspace", "Where are my biggest whitespace gaps?",
                   "Compare barrel-leg denim and wide-leg trousers"]


def build_agent_card() -> AgentCard:
    ext = AgentExtension(uri=v09.EXTENSION_URI, description="Renders A2UI v0.9 (GE composite catalog)",
                         required=False, params=v09.agent_extension_params())
    return AgentCard(
        protocol_version="0.3.0",
        name=DISPLAY_NAME,
        description=DESCRIPTION,
        url=config.AGENT_URL,
        version="0.1.0",
        default_input_modes=["text", "text/plain"],
        default_output_modes=["text", "text/plain"],
        capabilities=AgentCapabilities(streaming=True, extensions=[ext]),
        skills=[
            AgentSkill(id="workspace", name="Trend workspace",
                       description="Opportunity map, ranked list and drill-downs for tracked trends.",
                       tags=["trends", "analytics", "a2ui"], examples=["Open the trend workspace"]),
            AgentSkill(id="analysis", name="Trend analysis",
                       description="Compare trends, find whitespace gaps and assortment at risk, per brand.",
                       tags=["analysis", "assortment"],
                       examples=["Where are my biggest whitespace gaps?", "Compare barrel-leg denim and wide-leg trousers"]),
            AgentSkill(id="recommendations", name="Recommended actions",
                       description="Concrete buy, design and marketing actions for a trend, written into the workspace.",
                       tags=["recommendations"], examples=["Recommend actions for butter yellow"]),
        ],
    )
