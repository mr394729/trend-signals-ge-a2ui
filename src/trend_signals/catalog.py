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

"""Illustrative trend-signal data for a fictional apparel retailer.

Everything here is synthetic and deterministic (seeded) — the point of the
reference blueprint is the experience and the agent <-> canvas loop, not the
data source. Swap `build_dataset()` for a read of a governed data product
(e.g. BigQuery) and nothing else changes: the UI and the agent only see the
dict this module returns.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from functools import lru_cache
from typing import Any

RETAILER = "Cymbal Apparel"
BRANDS = [
    {"id": "core", "name": "Cymbal Core"},
    {"id": "studio", "name": "Cymbal Studio"},
    {"id": "active", "name": "Cymbal Active"},
    {"id": "kids", "name": "Cymbal Kids"},
]
LIFECYCLES = ["emerging", "growth", "peak", "mature", "decline"]
TYPES = {"style": "Style", "aesthetic": "Aesthetic", "fabric": "Fabric", "color": "Color"}
CHANNELS = [("tiktok", "TikTok", -3), ("pinterest", "Pinterest", -1), ("search", "Search", 0),
            ("editorial", "Editorial", 3), ("runway", "Runway", -6)]

HIST, FC = 26, 12  # weeks of history / forecast

# id, name, type, lifecycle, current strength, coverage %, brand fit (core, studio, active, kids),
# silhouette shape, palette hexes, silhouettes, fabrics, moods, cultural drivers
_SEEDS: list[tuple] = [
    ("t01", "Minimalist '90s", "aesthetic", "peak", 88, 58, (92, 74, 40, 30), "trousers",
     ["#2B2B2B", "#E8E4DC", "#8A8F98"], ["Straight leg", "Clean column", "Boxy tee"],
     ["Cotton poplin", "Matte jersey"], ["Understated", "Architectural", "Neutral"],
     ["Post-logo fatigue", "Capsule wardrobes", "Archival revival"]),
    ("t02", "Barrel-leg denim", "style", "growth", 74, 31, (88, 70, 25, 40), "trousers",
     ["#3B5A7A", "#7F9BB8", "#1F2D3F"], ["Barrel leg", "Mid rise", "Cropped hem"],
     ["Rigid denim", "Recycled denim"], ["Relaxed", "Utilitarian"],
     ["Comfort-first fit", "Creator styling videos"]),
    ("t03", "Quiet tailoring", "style", "growth", 68, 44, (66, 91, 12, 8), "jacket",
     ["#4B4036", "#C9BBA6", "#222831"], ["Soft shoulder", "Single-breasted", "Wide trouser"],
     ["Wool blend", "Washed twill"], ["Polished", "Understated"],
     ["Hybrid work", "Investment dressing"]),
    ("t04", "Butter yellow", "color", "growth", 72, 22, (72, 85, 60, 55), "tee",
     ["#F3E3A1", "#E9CF74", "#FFF7DA"], ["Knit tops", "Fluid skirts"],
     ["Ribbed knit", "Cotton jersey"], ["Warm", "Optimistic"],
     ["Soft-pastel social palettes", "Spring wedding season"]),
    ("t05", "Cherry red", "color", "peak", 90, 64, (80, 88, 52, 35), "dress",
     ["#9E1B32", "#C62E43", "#5E0F1D"], ["Outerwear", "Bags", "Knitwear"],
     ["Wool", "Satin", "Ribbed knit"], ["Confident", "Heritage"],
     ["Heritage-brand nostalgia", "Winter-holiday dressing"]),
    ("t06", "Sage & moss greens", "color", "mature", 55, 71, (60, 55, 66, 70), "hoodie",
     ["#9CAF88", "#6B7F5A", "#CBD5BD"], ["Layering pieces", "Sets"],
     ["Brushed fleece", "French terry"], ["Calm", "Outdoorsy"],
     ["Wellness routines", "Biophilic interiors"]),
    ("t07", "Chocolate brown", "color", "growth", 66, 28, (78, 84, 30, 22), "jacket",
     ["#4A2C21", "#7B5544", "#D2B9A4"], ["Leather-look outerwear", "Wide trousers"],
     ["Faux suede", "Corduroy"], ["Rich", "Grounded"],
     ["Tonal dressing", "Autumn runway echo"]),
    ("t08", "Cool cobalt", "color", "emerging", 42, 12, (45, 77, 50, 33), "dress",
     ["#1F4FBF", "#6F93E8", "#0E2A6B"], ["Statement knit", "Slip dress"],
     ["Satin", "Fine gauge knit"], ["Bold", "Electric"],
     ["Digital-native palettes", "Gallery-opening styling"]),
    ("t09", "Soft utility", "aesthetic", "growth", 63, 49, (82, 60, 71, 62), "jacket",
     ["#7C7A5E", "#C3BFA5", "#3A3D32"], ["Chore jacket", "Cargo pocket", "Overshirt"],
     ["Ripstop", "Washed canvas"], ["Practical", "Outdoors-adjacent"],
     ["Workwear crossover", "Trail-to-town"]),
    ("t10", "Coastal prep", "aesthetic", "mature", 54, 76, (74, 63, 28, 69), "tee",
     ["#1F3A5F", "#F5F1E8", "#A3B8CC"], ["Rugby stripe", "Polo knit", "Pleated short"],
     ["Pique cotton", "Linen blend"], ["Classic", "Seasonal"],
     ["Resort travel", "Modern-prep revival"]),
    ("t11", "Balletcore", "aesthetic", "decline", 30, 69, (40, 58, 36, 66), "skirt",
     ["#F0D5DA", "#C9A0A8", "#FFFFFF"], ["Wrap top", "Tulle skirt", "Flat shoe"],
     ["Mesh", "Satin", "Fine knit"], ["Soft", "Romantic"],
     ["Dance-media crossover"]),
    ("t12", "Western revival", "aesthetic", "peak", 84, 37, (62, 79, 35, 48), "jacket",
     ["#8A5A36", "#D8C3A5", "#2F2A26"], ["Yoke shirt", "Bootcut", "Fringe detail"],
     ["Suede-look", "Denim"], ["Rugged", "Nostalgic"],
     ["Festival season", "Country-music crossover"]),
    ("t13", "Dark academia knits", "aesthetic", "mature", 52, 61, (58, 76, 20, 28), "hoodie",
     ["#3E2F2A", "#7A6A5A", "#1B1F2A"], ["Cardigan", "Vest", "Pleated skirt"],
     ["Merino blend", "Cable knit"], ["Studious", "Layered"],
     ["Back-to-campus", "Book-community content"]),
    ("t14", "Performance-casual", "style", "growth", 76, 52, (60, 38, 94, 57), "hoodie",
     ["#2E3A4A", "#A5B4C4", "#E6E9ED"], ["Zip layer", "Tapered jogger", "Shell"],
     ["Technical stretch", "Quick-dry knit"], ["Athletic", "Versatile"],
     ["Commute-to-gym", "Wellness spending"]),
    ("t15", "Cropped boxy outerwear", "style", "peak", 82, 55, (70, 83, 45, 40), "jacket",
     ["#B8A58F", "#2A2A2A", "#E9E1D5"], ["Boxy crop", "Dropped shoulder"],
     ["Waxed cotton", "Faux shearling"], ["Structured", "Youthful"],
     ["High-rise bottoms", "Layering culture"]),
    ("t16", "Wide-leg pleated trouser", "style", "growth", 64, 40, (79, 82, 18, 20), "trousers",
     ["#3A3A3F", "#B9AE9A", "#E7E2D6"], ["Wide leg", "Pleated front"],
     ["Tropical wool", "Fluid crepe"], ["Elegant", "Easy"],
     ["Office-return wardrobes"]),
    ("t17", "Textured bouclé", "fabric", "growth", 58, 35, (50, 87, 10, 18), "jacket",
     ["#D9CFC1", "#8E8374", "#F4EFE6"], ["Cropped jacket", "Shell top"],
     ["Bouclé", "Tweed-look"], ["Tactile", "Refined"],
     ["Tactile-first social content", "Heritage luxury cues"]),
    ("t18", "Washed linen blends", "fabric", "peak", 80, 66, (85, 66, 31, 58), "tee",
     ["#CDBFA5", "#E7DFCF", "#8D8A7A"], ["Relaxed shirt", "Drawstring pant"],
     ["Linen-cotton", "Lyocell blend"], ["Breezy", "Natural"],
     ["Warm-weather travel", "Natural-fibre preference"]),
    ("t19", "Technical stretch poplin", "fabric", "growth", 60, 29, (68, 52, 82, 41), "trousers",
     ["#2F3B52", "#9FB0C8", "#EAEFF5"], ["Travel pant", "Shirt-jacket"],
     ["Nylon-cotton poplin", "4-way stretch"], ["Crisp", "Packable"],
     ["Business-travel recovery"]),
    ("t20", "Recycled-content denim", "fabric", "mature", 50, 74, (76, 61, 33, 72), "trousers",
     ["#4D6B8A", "#9AB3CC", "#27384A"], ["All denim silhouettes"],
     ["Recycled cotton", "Low-water wash"], ["Responsible", "Durable"],
     ["Sustainability disclosure", "Resale value"]),
    ("t21", "Brushed fleece heritage", "fabric", "decline", 26, 78, (51, 30, 62, 80), "hoodie",
     ["#8C7B6B", "#CFC3B5", "#43372E"], ["Quarter-zip", "Pullover"],
     ["Brushed fleece", "Sherpa"], ["Cosy", "Nostalgic"],
     ["Cold-snap demand spikes"]),
    ("t22", "Ribbed knit sets", "fabric", "emerging", 46, 18, (55, 72, 69, 44), "tee",
     ["#E3D6C8", "#B7A28B", "#5C4B3D"], ["Matching set", "Midi skirt"],
     ["Ribbed jersey", "Seamless knit"], ["Comfortable", "Put-together"],
     ["Elevated loungewear"]),
    ("t23", "Mini-skirt revival", "style", "emerging", 40, 20, (46, 81, 22, 12), "skirt",
     ["#1E1E24", "#C7B8A2", "#6E7B8B"], ["Pleated mini", "Skort"],
     ["Twill", "Denim"], ["Playful", "Nostalgic"],
     ["Y2K nostalgia cycle"]),
    ("t24", "Nature-tone outdoors", "aesthetic", "emerging", 38, 25, (52, 40, 88, 60), "hoodie",
     ["#59664A", "#A39A82", "#2A3328"], ["Shell layer", "Trail short"],
     ["Ripstop", "Softshell"], ["Outdoorsy", "Practical"],
     ["Hiking participation", "Trail-running crossover"]),
]

# SKU catalog the trends are matched against: name, brand, dept, shape, hex, price
_SKUS: list[tuple] = [
    ("p01", "Straight-Leg Cotton Trouser", "core", "Women's", "trousers", "#2B2B2B", 59),
    ("p02", "Relaxed Barrel Jean", "core", "Women's", "trousers", "#3B5A7A", 69),
    ("p03", "Soft-Shoulder Blazer", "studio", "Women's", "jacket", "#4B4036", 129),
    ("p04", "Ribbed Knit Tee", "core", "Women's", "tee", "#F3E3A1", 29),
    ("p05", "Satin Slip Dress", "studio", "Women's", "dress", "#9E1B32", 99),
    ("p06", "Brushed Fleece Hoodie", "kids", "Kids", "hoodie", "#9CAF88", 34),
    ("p07", "Faux-Suede Chore Jacket", "studio", "Women's", "jacket", "#7B5544", 119),
    ("p08", "Chore Overshirt", "core", "Men's", "jacket", "#7C7A5E", 79),
    ("p09", "Rugby Polo", "core", "Men's", "tee", "#1F3A5F", 49),
    ("p10", "Pleated Wide-Leg Trouser", "studio", "Women's", "trousers", "#3A3A3F", 89),
    ("p11", "Linen-Blend Shirt", "core", "Men's", "tee", "#CDBFA5", 54),
    ("p12", "Travel Stretch Pant", "active", "Men's", "trousers", "#2F3B52", 74),
    ("p13", "Zip Performance Layer", "active", "Women's", "hoodie", "#2E3A4A", 84),
    ("p14", "Cropped Boxy Jacket", "studio", "Women's", "jacket", "#B8A58F", 109),
    ("p15", "Recycled Straight Jean", "core", "Men's", "trousers", "#4D6B8A", 64),
    ("p16", "Quarter-Zip Fleece", "kids", "Kids", "hoodie", "#8C7B6B", 39),
    ("p17", "Pleated Mini Skirt", "studio", "Women's", "skirt", "#1E1E24", 49),
    ("p18", "Trail Shell", "active", "Men's", "jacket", "#59664A", 99),
    ("p19", "Merino Cardigan", "studio", "Women's", "hoodie", "#3E2F2A", 94),
    ("p20", "Western Yoke Shirt", "core", "Men's", "tee", "#8A5A36", 59),
    ("p21", "Tulle Wrap Skirt", "kids", "Kids", "skirt", "#F0D5DA", 32),
    ("p22", "Seamless Rib Set Top", "active", "Women's", "tee", "#E3D6C8", 44),
]
# trend -> [(sku, match%)] ; hand-wired so the coverage story is coherent
_MATCHES: dict[str, list[tuple[str, int]]] = {
    "t01": [("p01", 91), ("p09", 70), ("p10", 66)], "t02": [("p02", 94)],
    "t03": [("p03", 90), ("p10", 72)], "t04": [("p04", 77)], "t05": [("p05", 88), ("p17", 52)],
    "t06": [("p06", 83), ("p13", 60)], "t07": [("p07", 85)], "t08": [("p05", 41)],
    "t09": [("p08", 92), ("p18", 71), ("p07", 55)], "t10": [("p09", 93), ("p11", 61)],
    "t11": [("p21", 87), ("p17", 58)], "t12": [("p20", 90), ("p07", 54)],
    "t13": [("p19", 89), ("p17", 47)], "t14": [("p13", 95), ("p12", 78)],
    "t15": [("p14", 94), ("p03", 49)], "t16": [("p10", 93), ("p01", 62)],
    "t17": [("p14", 58)], "t18": [("p11", 90), ("p01", 51)], "t19": [("p12", 91)],
    "t20": [("p15", 92), ("p02", 63)], "t21": [("p16", 90), ("p06", 72)],
    "t22": [("p22", 88)], "t23": [("p17", 90)], "t24": [("p18", 86), ("p13", 56)],
}
_SOURCES = ["The Runway Ledger", "Thread & Trend Weekly", "Retail Pattern Review", "Social Signal Index"]
_ARTICLE_TEMPLATES = [
    "Why {n} keeps showing up in street-style roundups",
    "{n}: what the season's early sell-through suggests",
    "Buyers weigh in: is {n} a one-season story?",
    "How creators are styling {n} for autumn",
]


def _anchors(life: str, s: float) -> tuple[float, float]:
    """(value 25 weeks ago, value 12 weeks ahead) for a trend at strength s."""
    return {"emerging": (max(4.0, s * 0.15), min(92.0, s * 1.75)),
            "growth": (s * 0.35, min(96.0, s * 1.3)),
            "peak": (s * 0.55, s * 0.88),
            "mature": (min(95.0, s * 1.55), s * 0.72),
            "decline": (min(90.0, s * 2.4), s * 0.6)}[life]


def _series(rng: random.Random, life: str, strength: float, shift: int, noise: float) -> list[float]:
    """HIST + FC weekly index points (0-100): a smooth curve through
    (start, now, horizon) anchors; a channel with shift<0 leads the overall curve."""
    a, e = _anchors(life, strength)
    x0, x1, x2 = -(HIST - 1), 0.0, float(FC)

    def g(x: float) -> float:
        return (a * (x - x1) * (x - x2) / ((x0 - x1) * (x0 - x2))
                + strength * (x - x0) * (x - x2) / ((x1 - x0) * (x1 - x2))
                + e * (x - x0) * (x - x1) / ((x2 - x0) * (x2 - x1)))

    out = []
    for w in range(-HIST + 1, FC + 1):  # w=0 is "this week"
        v = g(w - shift)
        if w <= 0:
            v += rng.gauss(0, noise)
        out.append(round(max(2.0, min(100.0, v)), 1))
    return out


def _week_labels(today: date) -> list[str]:
    monday = today - timedelta(days=today.weekday())
    return [(monday + timedelta(weeks=w)).isoformat() for w in range(-HIST + 1, FC + 1)]


def _quick_read(t: dict[str, Any]) -> str:
    gap = t["strength"] >= 70 and t["coverage"] < 45
    if gap:
        return (f"Strong and rising demand ({t['strength']}) with only {t['coverage']}% assortment "
                f"coverage — a whitespace opportunity.")
    if t["life"] in ("decline", "mature") and t["coverage"] >= 65:
        return (f"Past its peak with {t['coverage']}% coverage — protect margin and avoid deepening buys.")
    if t["life"] == "emerging":
        return f"Early signal ({t['strength']}); watch the next 4 weeks before committing buys."
    return (f"Strength {t['strength']}, {'+' if t['momentum'] >= 0 else ''}{t['momentum']} over four weeks; "
            f"{t['coverage']}% covered.")


@lru_cache(maxsize=1)
def _build(today_iso: str) -> dict[str, Any]:
    today = date.fromisoformat(today_iso)
    weeks = _week_labels(today)
    skus = {p[0]: {"id": p[0], "name": p[1], "brand": p[2], "dept": p[3], "shape": p[4],
                   "hex": p[5], "price": p[6]} for p in _SKUS}
    for i, p in enumerate(skus.values()):
        r = random.Random(100 + i)
        p["sell_through"] = r.randint(38, 86)
        p["weeks_cover"] = r.randint(4, 21)

    trends = []
    for idx, (tid, name, ttype, life, amp, cov, fit, shape, pal, sil, fab, mood, drv) in enumerate(_SEEDS):
        rng = random.Random(idx * 7919 + 13)
        overall = _series(rng, life, amp, 0, 1.2)
        series = {"overall": overall}
        channels = []
        for cid, label, shift in CHANNELS:
            s = _series(random.Random(rng.random()), life, amp * rng.uniform(0.85, 1.08), shift, 2.0)
            series[cid] = s
            now = s[HIST - 1]
            channels.append({"id": cid, "label": label, "value": round(now),
                             "delta": round(now - s[HIST - 5])})
        now_i = HIST - 1
        strength = round(overall[now_i])
        momentum = round(overall[now_i] - overall[now_i - 4])
        # forecast band widens with horizon
        band = [[round(max(0, overall[now_i + k] - 3 - 1.6 * k), 1), round(min(100, overall[now_i + k] + 3 + 1.6 * k), 1)]
                for k in range(1, FC + 1)]
        fc_peak = max(range(HIST - 1, len(overall)), key=lambda i: overall[i])
        lc_pos = {"emerging": 0.12, "growth": 0.34, "peak": 0.55, "mature": 0.74, "decline": 0.92}[life]
        matches = [{"sku": s, "match": m} for s, m in _MATCHES.get(tid, [])]
        t = {
            "id": tid, "name": name, "type": ttype, "life": life, "strength": strength,
            "momentum": momentum, "coverage": cov,
            "volume": round(strength * rng.uniform(9, 14) / 1.0) * 10,
            "fit": dict(zip([b["id"] for b in BRANDS], fit)),
            "series": series, "band": band, "peak_week": weeks[min(fc_peak, len(weeks) - 1)],
            "lifecycle_pos": lc_pos, "channels": channels, "drivers": list(drv),
            "dna": {"palette": [{"hex": h, "name": n} for h, n in
                                zip(pal, ["Lead", "Support", "Accent"])],
                    "silhouettes": list(sil), "fabrics": list(fab), "moods": list(mood), "shape": shape},
            "products": matches,
            "articles": [{"title": tpl.format(n=name), "source": _SOURCES[(idx + k) % 4],
                          "date": (today - timedelta(days=3 + 5 * k + idx % 4)).isoformat()}
                         for k, tpl in enumerate(_ARTICLE_TEMPLATES[:3])],
        }
        t["quick_read"] = _quick_read(t)
        trends.append(t)
    return {"retailer": RETAILER, "brands": BRANDS, "types": TYPES, "lifecycles": LIFECYCLES,
            "weeks": weeks, "hist": HIST, "fc": FC, "as_of": weeks[HIST - 1],
            "trends": trends, "products": skus}


def dataset() -> dict[str, Any]:
    return _build(date.today().isoformat())


def trend(tid: str) -> dict[str, Any] | None:
    return next((t for t in dataset()["trends"] if t["id"] == tid), None)


def resolve(name_or_id: str) -> dict[str, Any] | None:
    q = (name_or_id or "").strip().lower()
    if not q:
        return None
    ts = dataset()["trends"]
    for t in ts:
        if t["id"] == q or t["name"].lower() == q:
            return t
    for t in ts:
        if q in t["name"].lower() or t["name"].lower() in q:
            return t
    return None
