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

"""The agent's tools. Each returns compact, grounded data; the ones that change
what the user sees do so through ui_state (the canvas is rendered by the executor)."""

from __future__ import annotations

import logging
from typing import Any

from google.adk.tools.tool_context import ToolContext


from trend_signals import catalog, ui_state
from trend_signals.kit import identity
from trend_signals.state import _opportunity

logger = logging.getLogger(__name__)
_BRAND_IDS = [b["id"] for b in catalog.BRANDS]
_VIEWS_HELP = "map | list | heatmap | timeline | detail | compare | board"



# Tool arguments come from the model, which a user can steer: bound every text field and list so one turn
# cannot grow the workspace state (one A2UI message is limited to 1 MiB) or the tool replies.
MAX_TEXT, MAX_REFS = 200, 24


def _clip(text: Any, n: int = MAX_TEXT) -> str:
    return str(text or "").strip()[:n]


def _refs(refs: list[str] | None, n: int = MAX_REFS) -> list[str]:
    return [_clip(r, 80) for r in (refs or [])[:n]]


def _limit(value: Any, default: int, top: int) -> int:
    try:
        return max(1, min(int(value), top))
    except (TypeError, ValueError):
        return default


def _user(tc: ToolContext) -> str:
    return identity.key_from_state(tc.state)


def _brand(b: str) -> str:
    b = (b or "").strip().lower().replace("cymbal ", "")
    return b if b in _BRAND_IDS else ""


def _row(t: dict[str, Any], brand: str = "") -> dict[str, Any]:
    r = {"id": t["id"], "name": t["name"], "type": t["type"], "lifecycle": t["life"],
         "strength": t["strength"], "momentum_4w": t["momentum"], "coverage_pct": t["coverage"],
         "opportunity": _opportunity(t)}
    if brand:
        r["brand_fit"] = t["fit"][brand]
    return r


def _find(ref: str) -> dict[str, Any] | None:
    return catalog.resolve(ref)


def _missing(ref: str) -> dict[str, Any]:
    names = [t["name"] for t in catalog.dataset()["trends"]]
    return {"error": f"No tracked trend matches {_clip(ref, 80)!r}.", "tracked_trends": names}


def search_trends(query: str = "", type: str = "", lifecycle: str = "", brand: str = "",
                  sort: str = "strength", limit: int = 8) -> dict[str, Any]:
    """Find tracked trends. All filters are optional.

    Args:
      query: words to match in the trend name, e.g. "denim", "red".
      type: style | aesthetic | fabric | color.
      lifecycle: emerging | growth | peak | mature | decline.
      brand: core | studio | active | kids (also ranks by that brand's fit).
      sort: strength | momentum | coverage | opportunity | fit.
      limit: max rows (default 8).
    """
    b = _brand(brand)
    q = _clip(query, 80).lower()
    rows = [t for t in catalog.dataset()["trends"]
            if (not q or q in t["name"].lower() or any(q in d.lower() for d in t["drivers"]))
            and (not type or t["type"] == type.lower())
            and (not lifecycle or t["life"] == lifecycle.lower())]
    key = {"strength": lambda t: -t["strength"], "momentum": lambda t: -t["momentum"],
           "coverage": lambda t: t["coverage"], "opportunity": lambda t: -_opportunity(t),
           "fit": lambda t: -(t["fit"][b] if b else 0)}.get(sort, lambda t: -t["strength"])
    rows.sort(key=key)
    return {"count": len(rows), "trends": [_row(t, b) for t in rows[:_limit(limit, 8, 24)]]}


def get_trend(trend: str) -> dict[str, Any]:
    """Everything known about one trend: numbers, forecast, channels, drivers, visual DNA, brand fit,
    matched SKUs with sell-through, and source articles.

    Args:
      trend: trend name or id, e.g. "Barrel-leg denim" or "t02".
    """
    t = _find(trend)
    if not t:
        return _missing(trend)
    ds = catalog.dataset()
    s = t["series"]["overall"]
    hist = ds["hist"]
    return {
        **_row(t), "quick_read": t["quick_read"],
        "forecast": {"in_4_weeks": round(s[hist - 1 + 4]), "in_12_weeks": round(s[-1]),
                     "expected_peak_week": t["peak_week"]},
        "channels": {c["label"]: {"index": c["value"], "change_4w": c["delta"]} for c in t["channels"]},
        "brand_fit": {b["name"]: t["fit"][b["id"]] for b in ds["brands"]},
        "drivers": t["drivers"],
        "visual_dna": {"palette": [p["hex"] for p in t["dna"]["palette"]], "silhouettes": t["dna"]["silhouettes"],
                       "fabrics": t["dna"]["fabrics"], "moods": t["dna"]["moods"]},
        "matched_products": [{**{k: ds["products"][m["sku"]][k] for k in ("id", "name", "brand", "sell_through", "weeks_cover")},
                              "match_pct": m["match"]} for m in t["products"]],
        "articles": [f"{a['title']} — {a['source']}, {a['date']}" for a in t["articles"]],
    }


def compare_trends(trends: list[str]) -> dict[str, Any]:
    """Compare two to four trends side by side.

    Args:
      trends: trend names or ids.
    """
    found, unknown = [], []
    for ref in _refs(trends, 8):
        (found if _find(ref) else unknown).append(_find(ref) or ref)
    if len(found) < 2:
        return {"error": "Need at least two tracked trends to compare.", "unmatched": unknown}
    ds = catalog.dataset()
    return {"unmatched": unknown, "trends": [
        {**_row(t), "forecast_12w": round(t["series"]["overall"][-1]),
         "top_channel": max(t["channels"], key=lambda c: c["value"])["label"],
         "brand_fit": {b["name"]: t["fit"][b["id"]] for b in ds["brands"]}} for t in found[:4]]}


def scan_assortment(brand: str = "", limit: int = 5) -> dict[str, Any]:
    """Where to act: whitespace opportunities (strong demand, thin coverage) and assortment at risk
    (fading trend, heavy coverage). Optionally weighted by a brand's fit.

    Args:
      brand: core | studio | active | kids (optional).
      limit: rows per list (default 5).
    """
    b = _brand(brand)
    ts = catalog.dataset()["trends"]
    n = _limit(limit, 5, 10)

    def score(t: dict[str, Any]) -> float:
        return _opportunity(t) * ((t["fit"][b] / 100) if b else 1)

    gaps = sorted((t for t in ts if t["life"] in ("emerging", "growth", "peak") and t["coverage"] < 60),
                  key=lambda t: -score(t))[:n]
    risks = sorted((t for t in ts if t["life"] in ("mature", "decline") and t["coverage"] >= 55),
                   key=lambda t: -t["coverage"])[:n]
    return {"brand": b or "all", "whitespace_opportunities": [_row(t, b) for t in gaps],
            "assortment_at_risk": [_row(t, b) for t in risks]}


def show_in_canvas(view: str, trend: str = "", compare: list[str] | None = None,
                   highlight: list[str] | None = None, type: str = "", lifecycle: str = "",
                   brand: str = "", query: str = "", note: str = "",
                   tool_context: ToolContext = None) -> dict[str, Any]:
    """Update the workspace canvas next to the chat. Call it at the end of an analysis.

    Args:
      view: map (opportunity map) | list (ranked list) | heatmap (every trend against every brand's fit) |
            timeline (all demand curves ordered by peak week) | detail (one trend; set `trend`) |
            compare (side-by-side; set `compare`) | board (the user's shortlist).
      trend: trend name or id for the detail view.
      compare: two to three trend names or ids for the compare view.
      highlight: trend names or ids to point out on the map or list, usually the ones you name in your
        reply. Everything else is dimmed, so use it for a short list (up to about eight).
      type: filter, style | aesthetic | fabric | color (map and list views).
      lifecycle: filter, emerging | growth | peak | mature | decline.
      brand: filter, core | studio | active | kids.
      query: free-text filter on the trend name.
      note: one short sentence shown as an "Agent" banner on the canvas saying what you highlighted.
    """
    user = _user(tool_context)
    if view not in ui_state.VIEWS:
        return {"error": f"view must be one of {_VIEWS_HELP}"}
    ui = ui_state.get_ui(user)
    sel = None
    if view == "detail":
        t = _find(trend)
        if not t:
            return _missing(trend)
        sel = t["id"]
    if view == "compare":
        ids = [t["id"] for t in (_find(r) for r in _refs(compare, 6)) if t]
        if len(ids) < 2:
            return {"error": "compare view needs two or three tracked trends in `compare`."}
        ui["cmp"] = list(dict.fromkeys(ids))[:3]
    _navigate(ui, view, sel)
    if view in ("map", "list", "heatmap", "timeline"):
        ui["f"] = {"type": type.lower(), "brand": _brand(brand), "life": lifecycle.lower(), "q": _clip(query, 80)}
        ui["hl"] = list(dict.fromkeys(t["id"] for t in (_find(r) for r in _refs(highlight)) if t))[:10]
    if note:
        ui_state.set_note(user, note[:200])
    ui_state.request_update(user)
    return {"ok": True, "canvas": ui_state.describe(user, {t["id"]: t["name"] for t in catalog.dataset()["trends"]})}


def update_board(add: list[str] | None = None, remove: list[str] | None = None,
                 tool_context: ToolContext = None) -> dict[str, Any]:
    """Add or remove trends on the user's board (their shortlist).

    Args:
      add: trend names or ids to add.
      remove: trend names or ids to remove.
    """
    user = _user(tool_context)
    ui = ui_state.get_ui(user)
    unknown = []
    for ref in _refs(add):
        t = _find(ref)
        if not t:
            unknown.append(ref)
        elif t["id"] not in ui["board"]:
            ui["board"].append(t["id"])
    for ref in _refs(remove):
        t = _find(ref)
        if t and t["id"] in ui["board"]:
            ui["board"].remove(t["id"])
    ui_state.request_update(user)
    names = {t["id"]: t["name"] for t in catalog.dataset()["trends"]}
    return {"board": [names[i] for i in ui["board"]], "unmatched": unknown}


def _navigate(ui: dict[str, Any], view: str, sel: str | None = None) -> None:
    """Move the canvas to a view (and trend). A different page starts at the top; the same page keeps
    the user's scroll position."""
    changed = view != ui["view"] or (sel is not None and sel != ui["sel"])
    ui["view"] = view
    if sel is not None:
        ui["sel"] = sel
    if changed:
        ui["sy"] = 0


_PRIORITIES = {"high", "medium", "low"}


def save_recommendations(trend: str, actions: list[str], tool_context: ToolContext = None) -> dict[str, Any]:
    """Write 2-4 recommended actions for a trend into the canvas (detail view).

    Args:
      trend: trend name or id.
      actions: each string is "priority | owner | timing | action | why" with priority one of
        high/medium/low, e.g. "high | Women's buyer | next 2 weeks | Add two barrel-leg SKUs to Core
        Q1 buy | Coverage is 31% against strength 74".
    """
    t = _find(trend)
    if not t:
        return _missing(trend)
    parsed, bad = [], []
    for a in (actions or [])[:8]:
        p = [_clip(x) for x in str(a).split("|")]
        if len(p) != 5 or p[0].lower() not in _PRIORITIES or not all(p):
            bad.append(_clip(a))
            continue
        parsed.append({"priority": p[0].lower(), "owner": p[1], "timing": p[2], "action": p[3], "why": p[4]})
    if bad or not parsed:
        return {"error": "Each action must be 'priority | owner | timing | action | why' with priority "
                         "high, medium or low. Fix and call again.", "rejected": bad}
    user = _user(tool_context)
    ui_state.get_recs(user)[t["id"]] = parsed[:4]
    _navigate(ui_state.get_ui(user), "detail", t["id"])
    ui_state.request_update(user)
    return {"saved": len(parsed[:4]), "trend": t["name"], "canvas": "detail view will show them"}


TOOLS = [search_trends, get_trend, compare_trends, scan_assortment, show_in_canvas, update_board,
         save_recommendations]
