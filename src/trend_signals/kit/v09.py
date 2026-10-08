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

"""A2UI v0.9 builders for Gemini Enterprise (GE-proven wire shape).

What makes v0.9 render in GE (verified live, Sept 2026; an earlier
attempt failed on the first two points):

* ``createSurface.catalogId`` must be GE's COMPOSITE catalog (basic +
  material + GE components such as Canvas / IFrameSrcdoc / Stepper). The
  basic catalog id gives "Catalog not found" / "Component type not found".
* The agent card's v0.9 extension must declare ``supportedCatalogIds``, or GE
  binds the surface to the basic catalog regardless of ``catalogId``.
* ``createSurface`` is a strict object: surfaceId, catalogId, optional theme /
  sendDataModel — nothing else (a stray ``root`` kills the surface).
* The renderer mounts the component whose id is literally ``root``.
* Components accept ONLY declared properties (unevaluatedProperties: false).
  ``Surface.messages`` validates every surface with the public A2UI Agent SDK
  against the composite catalog (``trend_signals.kit.sdk``).

Surfaces are fresh per turn (unique surfaceId): a createSurface for an existing id resets
that surface, and Gemini Enterprise reopens a Canvas panel when its surface is created.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

VERSION = "v0.9"
COMPOSITE_CATALOG_ID = (
    "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/"
    "gemini_enterprise_composite_catalog.json"
)
EXTENSION_URI = "https://a2ui.org/a2a-extension/a2ui/v0.9"


class Path_:  # noqa: N801 — reads as ``P("/form/title")`` at call sites
    """A data-model binding ``{"path": ...}``."""

    def __init__(self, path: str) -> None:
        self.path = path


P = Path_


def dyn(value: Any) -> Any:
    """Literal values pass through; ``P(...)`` becomes a binding."""
    return {"path": value.path} if isinstance(value, Path_) else value


_NON_MARKDOWN_VARIANTS = {"h1", "h2", "h3", "h4", "h5", "caption"}
_MARKDOWN_RE = re.compile(r"\*\*|__|\[[^\]]+\]\(|`|^#|^\s*[-*] ", re.M)


class Surface:
    """Accumulates flat v0.9 components; emits createSurface/updateDataModel/
    updateComponents for one fresh surface."""

    def __init__(self, prefix: str, surface_id: str | None = None,
                 create: bool = True) -> None:
        self.surface_id = surface_id or f"{prefix}-{uuid.uuid4().hex[:8]}"
        self.create = create
        self.components: list[dict[str, Any]] = []
        self._n = 0

    def add(self, component: str, cid: str | None = None, **props: Any) -> str:
        if cid is None:
            self._n += 1
            cid = f"{component[:1].lower()}{component[1:]}{self._n}"
        comp = {"id": cid, "component": component}
        comp.update({k: dyn(v) for k, v in props.items() if v is not None})
        self.components.append(comp)
        return cid

    # ---- layout
    def column(self, children: list[str], cid: str | None = None, **kw: Any) -> str:
        return self.add("Column", cid, children=children, **kw)

    def row(self, children: list[str], cid: str | None = None, **kw: Any) -> str:
        return self.add("Row", cid, children=children, **kw)

    def card(self, child: str, cid: str | None = None) -> str:
        return self.add("Card", cid, child=child)

    def divider(self) -> str:
        return self.add("Divider")

    def tabs(self, tabs: list[tuple[str, str]], cid: str | None = None) -> str:
        return self.add("Tabs", cid, tabs=[{"title": t, "child": c} for t, c in tabs])

    # ---- display
    def text(self, text: Any, variant: str | None = None, cid: str | None = None) -> str:
        """Basic ``Text`` skips markdown for h1-h5 and caption (GE renders the raw
        characters), so markdown in those variants goes out as ``MaterialText``,
        which always renders markdown."""
        if (variant in _NON_MARKDOWN_VARIANTS and isinstance(text, str)
                and _MARKDOWN_RE.search(text)):
            return self.add("MaterialText", cid, text=text, usageHint=variant)
        return self.add("Text", cid, text=text, variant=variant)

    def _labelled(self, label: str | None, field_id: str, cid: str | None) -> str:
        """GE does not render the label of TextField, ChoicePicker or
        DateTimeInput (DateTimeInput uses it for aria only), so a visible label
        sits above the field."""
        if not label:
            return field_id
        return self.column([self.add("MaterialText", text=label, usageHint="subtitle2"), field_id], cid)

    def icon(self, name: str) -> str:
        return self.add("Icon", name=name)

    # ---- input
    def button(self, label: str, action: str, context: dict[str, Any] | None = None,
               primary: bool = False, cid: str | None = None,
               prompt: str | None = None) -> str:
        """``prompt`` is the sentence GE shows in the user's chat bubble for the
        click (GE reads ``action.context.prompt``); without it GE shows the
        generic "User action triggered.". Defaults to the button label."""
        label_id = self.text(label)
        event: dict[str, Any] = {"name": action}
        ctx = {k: dyn(v) for k, v in (context or {}).items() if v is not None}
        ctx["prompt"] = prompt or label
        event["context"] = ctx
        return self.add("Button", cid, child=label_id, action={"event": event},
                        variant="primary" if primary else None)

    def choice_picker(self, options: list[tuple[str, str]], value: Any, *,
                      label: str | None = None, multi: bool = False,
                      chips: bool = False,
                      cid: str | None = None) -> str:
        picker = self.add(
            "ChoicePicker", None, label=label,
            options=[{"label": lbl, "value": val} for lbl, val in options],
            value=value,
            variant="multipleSelection" if multi else "mutuallyExclusive",
            displayStyle="chips" if chips else None,
        )
        return self._labelled(label, picker, cid)

    def select(self, options: list[tuple[str, str]], value: Any, *, label: str,
               placeholder: str = "Select", cid: str | None = None) -> str:
        """A dropdown (MaterialSelect): one value, bound to a string in the data model."""
        return self.add("MaterialSelect", cid, label=label, placeholder=placeholder, value=value,
                        options=[{"label": lbl, "value": val} for lbl, val in options])

    def text_field(self, label: str, value: Any, *, long: bool = False,
                   cid: str | None = None) -> str:
        field = self.add("TextField", None, label=label, value=value,
                         variant="longText" if long else None)
        return self._labelled(label, field, cid)

    def date_input(self, label: str, value: Any, cid: str | None = None) -> str:
        field = self.add("DateTimeInput", None, label=label, value=value, enableDate=True)
        return self._labelled(label, field, cid)

    # ---- GE side panel
    def canvas(self, *, title: str, description: str, icon: str, child: str,
               auto_open: bool = True) -> str:
        return self.add("Canvas", "root", cardTitle=title, cardDescription=description,
                        cardIcon=icon, autoOpen=auto_open, autoFullscreen=False,
                        children=[child])

    def iframe(self, html: str, title: str, cid: str | None = None,
               height: int | None = None) -> str:
        """Without ``height`` GE sizes the frame as a 4:3 box (also in Canvas)."""
        return self.add("IFrameSrcdoc", cid, title=title, htmlContent=html, height=height)

    # ---- emission
    def messages(self, data_model: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if not any(c["id"] == "root" for c in self.components):
            raise ValueError("A2UI v0.9: one component must have id 'root'")
        out: list[dict[str, Any]] = []
        if self.create:
            out.append({"version": VERSION, "createSurface": {
                "surfaceId": self.surface_id, "catalogId": COMPOSITE_CATALOG_ID}})
        # components first so bindings resolve against a mounted tree
        out.append({"version": VERSION, "updateComponents": {
            "surfaceId": self.surface_id, "components": self.components}})
        if data_model is not None:
            out.append({"version": VERSION, "updateDataModel": {
                "surfaceId": self.surface_id, "path": "/", "value": data_model}})
        from trend_signals.kit import sdk

        # Update-only batches target a surface created earlier; validate them against a stand-in.
        sdk.validate(out if self.create else [{"version": VERSION, "createSurface": {
            "surfaceId": self.surface_id, "catalogId": COMPOSITE_CATALOG_ID}}] + out)
        return out


def text_surface(prefix: str, message: str) -> list[dict[str, Any]]:
    s = Surface(prefix)
    t = s.text(message)
    s.column([t], cid="root")
    return s.messages()


def markdown_headings(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """A Basic ``Text`` with an h1-h5 or caption variant shows markdown as raw
    characters in GE; such a component becomes ``MaterialText``, which renders it.
    Used on model-generated cards (Pattern 1), where the model picks the variant."""
    out = []
    for c in components:
        if (c.get("component") == "Text" and c.get("variant") in _NON_MARKDOWN_VARIANTS
                and isinstance(c.get("text"), str) and _MARKDOWN_RE.search(c["text"])):
            c = {**{k: v for k, v in c.items() if k != "variant"}, "component": "MaterialText",
                 "usageHint": c["variant"]}
        out.append(c)
    return out


def delete_surface(surface_id: str) -> dict[str, Any]:
    """Removes a surface; Gemini Enterprise also closes the Canvas panel showing it."""
    return {"version": VERSION, "deleteSurface": {"surfaceId": surface_id}}


def agent_extension_params() -> dict[str, Any]:
    """Params of the SDK's A2UI v0.9 AgentExtension (composite catalog, no inline catalogs)."""
    from trend_signals.kit import sdk

    return dict(sdk.agent_extension().params or {})
