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

"""The public A2UI Agent SDK (a2ui-agent-sdk), configured for Gemini Enterprise.

One place that binds the SDK to Gemini Enterprise's composite catalog:

* `agent_extension()`   the A2UI v0.9 AgentExtension for the agent card (get_a2ui_agent_extension)
* `parts(messages)`     A2A parts for A2UI messages (create_a2ui_part)
* `validate(messages)`  schema + integrity validation against the composite catalog (A2uiCatalog.validate)
* `prompt(...)`         system-prompt text that teaches a model the catalog (DirectJsonFormat prompt generator)
* `parse(text)`         model output with <a2ui-json> blocks -> (text, A2UI messages) (DirectJsonParser)

One adjustment to the published catalog when it is loaded: several component properties that take a
JSON object (VegaChart.spec, InteractiveChart.chartData, RichTable.tableData, WebAppFrameUrl.config and
others) are typed as common_types `DynamicValue`, which in the SDK's v0.9 common types allows only
string, number, boolean, array, binding or function call. Gemini Enterprise renders object values for
these properties, so `GeCompositeCatalogProvider` lets each of them also accept an object.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

from a2ui.a2a.extension import get_a2ui_agent_extension
from a2ui.a2a.parts import create_a2ui_part
from a2ui.inference_formats.direct_json import DirectJsonFormat
from a2ui.schema.catalog import CatalogConfig
from a2ui.schema.catalog_provider import A2uiCatalogProvider
from a2ui.schema.constants import VERSION_0_9

COMPOSITE_CATALOG_ID = (
    "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json"
)
# Copy of the published catalog (refresh it when Gemini Enterprise publishes changes).
CATALOG_FILE = Path(__file__).resolve().parent / "ge_composite_catalog_v0_9.json"


_DYNAMIC_VALUE = "common_types.json#/$defs/DynamicValue"


def _accept_objects(node: Any) -> int:
    """Rewrite each component property typed DynamicValue to DynamicValue-or-object. Returns the count."""
    n = 0
    if isinstance(node, dict):
        for key, value in list(node.items()):
            if isinstance(value, dict) and str(value.get("$ref", "")).endswith(_DYNAMIC_VALUE):
                ref = {"$ref": value["$ref"]}
                rest = {k: v for k, v in value.items() if k != "$ref"}
                node[key] = {**rest, "anyOf": [ref, {"type": "object"}]}
                n += 1
            else:
                n += _accept_objects(value)
    elif isinstance(node, list):
        n += sum(_accept_objects(v) for v in node)
    return n


class GeCompositeCatalogProvider(A2uiCatalogProvider):
    """Loads the composite catalog file; object-valued DynamicValue properties also accept objects."""

    def __init__(self, path: Path = CATALOG_FILE) -> None:
        self.path = path

    def load(self) -> dict[str, Any]:
        catalog = json.loads(self.path.read_text())
        components = copy.deepcopy(catalog["components"])
        if not _accept_objects(components):
            raise RuntimeError(f"{self.path}: no DynamicValue component properties found; "
                               "check whether the catalog's object typing changed and update sdk.py")
        return {**catalog, "components": components}


@lru_cache(maxsize=1)
def a2ui_format() -> DirectJsonFormat:
    return DirectJsonFormat(VERSION_0_9, catalogs=[
        CatalogConfig(name="gemini_enterprise_composite", provider=GeCompositeCatalogProvider())])


@lru_cache(maxsize=1)
def catalog():
    return a2ui_format().get_selected_catalog()


def agent_extension():
    """Gemini Enterprise needs the composite catalog in supportedCatalogIds; it accepts no inline catalogs."""
    return get_a2ui_agent_extension(VERSION_0_9, accepts_inline_catalogs=False,
                                    supported_catalog_ids=[COMPOSITE_CATALOG_ID])


def parts(messages: Sequence[dict[str, Any]]):
    return [create_a2ui_part(m) for m in messages]


def validate(messages: Sequence[dict[str, Any]]) -> None:
    """Raises ValueError (from the SDK validator) if the messages would be rejected."""
    catalog().validate(list(messages))


def prompt(role: str, ui_description: str, allowed_components: Sequence[str] | None = None) -> str:
    return a2ui_format().prompt_generator.generate(
        role_description=role, ui_description=ui_description,
        allowed_components=list(allowed_components) if allowed_components else None,
        include_schema=True)


def parse(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Split model output into its text and the A2UI messages in its <a2ui-json> blocks.

    Uses the parser directly rather than parse_content_to_parts, which logs and drops parse errors;
    here a missing or malformed block raises A2uiParseError.
    """
    texts: list[str] = []
    messages: list[dict[str, Any]] = []
    for part in a2ui_format().parser.parse_response(text):
        if part.text and part.text.strip():
            texts.append(part.text.strip())
        if part.a2ui_json:
            messages += part.a2ui_json if isinstance(part.a2ui_json, list) else [part.a2ui_json]
    return "\n\n".join(texts), messages
