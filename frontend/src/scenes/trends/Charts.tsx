/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { max } from "d3-array";
import { scaleLinear, scaleSqrt } from "d3-scale";
import { area, curveMonotoneX, line } from "d3-shape";
import { motion } from "motion/react";
import { useId, useMemo, useRef, useState } from "react";
import { Tip } from "@/components";
import { LIFE_COLOR, LIFE_LABEL, weekLabel, type Life, type Trend, type TrendsState } from "@/lib/trends";

// ---------------------------------------------------------------------------
// Opportunity map: strength (x) against assortment coverage gap (y); bubble = search volume,
// color = lifecycle stage. Top-right is "strong demand, thin coverage".
// Positions are exact: bubbles overlap rather than being nudged.
// ---------------------------------------------------------------------------

const MW = 640, MH = 390, PADL = 46, PADR = 18, PADT = 16, PADB = 40;
const X_SPLIT = 60, Y_SPLIT = 55; // strength >= 60, coverage gap >= 55 (coverage < 45)

interface Pos { id: string; name: string; cx: number; cy: number; r: number }
interface Label { x: number; y: number; anchor: "start" | "middle" | "end" }

/** Greedy label placement: try above, right, left, below each bubble; skip a label that would
 * overlap another label or a bubble. Skipped names still show on hover. */
function placeLabels(items: Pos[], priority: string[]): Map<string, Label> {
  const placed: { x0: number; x1: number; y0: number; y1: number }[] = [];
  const out = new Map<string, Label>();
  type Box = { x0: number; x1: number; y0: number; y1: number };
  const blocked = (b: Box, own: string, strict: boolean) =>
    b.x0 < PADL || b.x1 > MW - PADR || b.y0 < PADT || b.y1 > MH - PADB
    || placed.some((o) => b.x0 < o.x1 && b.x1 > o.x0 && b.y0 < o.y1 && b.y1 > o.y0)
    || (strict && items.some((c) => c.id !== own && circleHits(c, b)));
  // Pass 1 keeps labels clear of every bubble; pass 2 lets the rest sit over a neighbouring bubble
  // (the label has a white halo) but never over another label.
  for (const strict of [true, false]) {
    for (const id of priority) {
      const it = items.find((i) => i.id === id);
      if (!it || out.has(id)) continue;
      const w = it.name.length * 6.5 + 6;
      const cands: Label[] = [
        { x: it.cx, y: it.cy - it.r - 6, anchor: "middle" },
        { x: it.cx + it.r + 6, y: it.cy + 4, anchor: "start" },
        { x: it.cx - it.r - 6, y: it.cy + 4, anchor: "end" },
        { x: it.cx, y: it.cy + it.r + 15, anchor: "middle" },
      ];
      for (const c of cands) {
        const x0 = c.anchor === "middle" ? c.x - w / 2 : c.anchor === "start" ? c.x : c.x - w;
        const box = { x0, x1: x0 + w, y0: c.y - 12, y1: c.y + 3 };
        if (!blocked(box, id, strict)) {
          placed.push(box);
          out.set(id, c);
          break;
        }
      }
    }
  }
  return out;
}

function circleHits(c: Pos, b: { x0: number; x1: number; y0: number; y1: number }): boolean {
  const nx = Math.max(b.x0, Math.min(c.cx, b.x1));
  const ny = Math.max(b.y0, Math.min(c.cy, b.y1));
  return (c.cx - nx) ** 2 + (c.cy - ny) ** 2 < (c.r + 1) ** 2;
}

export function OpportunityMap({ trends, matches, selected, board, highlight, onOpen }: {
  trends: Trend[]; matches: Set<string>; selected: string; board: string[]; highlight: string[];
  onOpen: (id: string, at?: { x: number; y: number }) => void;
}) {
  const x = scaleLinear().domain([0, 100]).range([PADL, MW - PADR]);
  const y = scaleLinear().domain([0, 100]).range([MH - PADB, PADT]); // gap = 100 - coverage
  const maxVol = max(trends, (t) => t.volume) ?? 1;
  const rad = scaleSqrt().domain([0, maxVol]).range([5, 17]);
  const ordered = useMemo(() => [...trends].sort((a, b) => b.volume - a.volume), [trends]); // big first
  const labels = useMemo(() => {
    const items: Pos[] = trends.filter((t) => matches.has(t.id)).map((t) => ({
      id: t.id, name: t.name, cx: x(t.strength), cy: y(100 - t.coverage), r: rad(t.volume) }));
    const order = [...trends].filter((t) => matches.has(t.id))
      .sort((a, b) => (b.id === selected ? 1 : 0) - (a.id === selected ? 1 : 0)
        || (highlight.includes(b.id) ? 1 : 0) - (highlight.includes(a.id) ? 1 : 0)
        || b.strength * (100 - b.coverage) - a.strength * (100 - a.coverage)).map((t) => t.id);
    return placeLabels(items, order.slice(0, highlight.length ? 10 : 9));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trends, matches, selected, highlight]);

  return (
    <div>
      <svg viewBox={`0 0 ${MW} ${MH}`} className="block h-auto w-full" role="img"
        aria-label="Opportunity map: trend strength against assortment coverage gap">
        <rect x={x(X_SPLIT)} y={PADT} width={MW - PADR - x(X_SPLIT)} height={y(Y_SPLIT) - PADT} className="fill-[var(--ws-tint)]" />
        {[0, 25, 50, 75, 100].map((g) => (
          <g key={g}>
            <line x1={PADL} x2={MW - PADR} y1={y(g)} y2={y(g)} className="stroke-line2" />
            <text x={PADL - 8} y={y(g) + 4} textAnchor="end" className="fill-ink4 text-[11px]">{100 - g}%</text>
            <line x1={x(g)} x2={x(g)} y1={PADT} y2={MH - PADB} className="stroke-line2" />
            <text x={x(g)} y={MH - PADB + 16} textAnchor="middle" className="fill-ink4 text-[11px]">{g}</text>
          </g>
        ))}
        <line x1={x(X_SPLIT)} x2={x(X_SPLIT)} y1={PADT} y2={MH - PADB} className="stroke-ink4" strokeDasharray="5 5" />
        <line x1={PADL} x2={MW - PADR} y1={y(Y_SPLIT)} y2={y(Y_SPLIT)} className="stroke-ink4" strokeDasharray="5 5" />
        <text x={MW - PADR - 8} y={PADT + 18} textAnchor="end" className="fill-accent font-serif text-[14px] ">Whitespace</text>
        <text x={MW - PADR - 8} y={MH - PADB - 8} textAnchor="end" className="fill-ink4 font-serif text-[13px] ">Defend &amp; scale</text>
        <text x={PADL + 8} y={PADT + 18} className="fill-ink4 font-serif text-[13px] ">Test small</text>
        <text x={PADL + 8} y={MH - PADB - 8} className="fill-ink4 font-serif text-[13px] ">Run down</text>
        <text x={(PADL + MW - PADR) / 2} y={MH - 6} textAnchor="middle" className="fill-ink3 text-[11px] font-semibold">
          Trend strength (0–100) →
        </text>
        <text transform={`translate(12 ${(PADT + MH - PADB) / 2}) rotate(-90)`} textAnchor="middle"
          className="fill-ink3 text-[11px] font-semibold">Assortment coverage (lower = bigger gap)</text>

        {ordered.map((t, i) => {
          const on = matches.has(t.id);
          const cx = x(t.strength), cy = y(100 - t.coverage), r = rad(t.volume);
          const lab = labels.get(t.id);
          return (
            <Tip key={t.id} content={
              <div className="space-y-0.5">
                <div className="font-serif text-[14px] font-medium">{t.name}</div>
                <div className="opacity-75">{LIFE_LABEL[t.life]} · strength {t.strength} ·
                  {" "}{t.momentum >= 0 ? "+" : ""}{t.momentum} over 4 weeks</div>
                <div className="opacity-75">{t.coverage}% covered · gap {100 - t.coverage}</div>
              </div>}>
              <motion.g className={on ? "cursor-pointer outline-none" : "pointer-events-none"}
                initial={{ opacity: 0, scale: 0.6 }} animate={{ opacity: on ? 1 : 0.13, scale: 1 }}
                whileHover={on ? { scale: 1.12 } : undefined}
                transition={{ delay: i * 0.012, type: "spring", stiffness: 260, damping: 22 }}
                style={{ transformOrigin: `${cx}px ${cy}px` }}
                onClick={(e) => on && onOpen(t.id, { x: e.clientX, y: e.clientY })} tabIndex={on ? 0 : -1} role="button"
                aria-label={`${t.name}, strength ${t.strength}, coverage ${t.coverage}%`}
                onKeyDown={(e) => on && (e.key === "Enter" || e.key === " ") && onOpen(t.id)}>
                <circle cx={cx} cy={cy} r={r} fill={LIFE_COLOR[t.life]} fillOpacity={0.8} stroke="var(--surface)"
                  strokeWidth={t.id === selected ? 3 : 2} />
                {highlight.includes(t.id) && <circle cx={cx} cy={cy} r={r + 6} fill="none" className="hl-ring" />}
                {board.includes(t.id) && <circle cx={cx} cy={cy} r={r + 4} fill="none" stroke="var(--ink)" strokeWidth="1.6" strokeDasharray="3 3" />}
                {on && lab && (
                  <text x={lab.x} y={lab.y} textAnchor={lab.anchor}
                    className="pointer-events-none fill-ink font-serif text-[13px] font-medium "
                    style={{ paintOrder: "stroke", stroke: "var(--surface)", strokeWidth: 3.5, strokeLinejoin: "round" }}>{t.name}</text>
                )}
              </motion.g>
            </Tip>
          );
        })}
      </svg>
      <Legend />
    </div>
  );
}

export function Legend() {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-2 pt-1 text-[11.5px] text-ink3" aria-label="Lifecycle legend">
      {(Object.keys(LIFE_LABEL) as Life[]).map((l) => (
        <span key={l} className="inline-flex items-center gap-1.5">
          <i className="inline-block size-2.5 rounded-full" style={{ background: LIFE_COLOR[l] }} />{LIFE_LABEL[l]}
        </span>
      ))}
      <span className="ml-auto">Bubble size = search volume · dashed ring = on your board</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Line chart: history (solid, drawn in) + forecast (dashed, widening band). Hover reads a week;
// drag to zoom into a range, double-click to reset. One trend (with band) or up to three to compare.
// ---------------------------------------------------------------------------

export interface Line { id: string; label: string; color: string; values: number[]; band?: [number, number][] }

const LW = 640, LH = 270, LPL = 36, LPR = 14, LPT = 14, LPB = 28;

export function LineChart({ lines, state }: { lines: Line[]; state: TrendsState }) {
  const { hist, weeks } = state;
  const n = weeks.length;
  const uid = useId().replace(/:/g, "");
  const ref = useRef<SVGSVGElement>(null);
  const [zoom, setZoom] = useState<[number, number] | null>(null);
  const [drag, setDrag] = useState<[number, number] | null>(null);
  const [hi, setHi] = useState<number | null>(null);
  const lo = zoom ? zoom[0] : 0, top = zoom ? zoom[1] : n - 1;
  const x = scaleLinear().domain([lo, top]).range([LPL, LW - LPR]);
  const y = scaleLinear().domain([0, 100]).range([LH - LPB, LPT]);
  const gen = line<number>().x((_, i) => x(i)).y((v) => y(v)).curve(curveMonotoneX);
  const idxAt = (clientX: number) => {
    const box = ref.current?.getBoundingClientRect();
    if (!box) return 0;
    const px = ((clientX - box.left) / box.width) * LW;
    return Math.max(0, Math.min(n - 1, Math.round(x.invert(px))));
  };
  const ticks = useMemo(() => {
    const step = Math.max(1, Math.round((top - lo) / 6));
    return Array.from({ length: Math.floor((top - lo) / step) + 1 }, (_, k) => lo + k * step);
  }, [lo, top]);
  const one = lines.length === 1 ? lines[0] : null;
  const sel = drag ? [Math.min(...drag), Math.max(...drag)] : null;

  return (
    <div className="relative">
      <svg ref={ref} viewBox={`0 0 ${LW} ${LH}`} className="block h-auto w-full touch-none select-none" role="img"
        aria-label={`Demand index over time for ${lines.map((l) => l.label).join(", ")}`}
        onPointerDown={(e) => { const i = idxAt(e.clientX); setDrag([i, i]); }}
        onPointerMove={(e) => { const i = idxAt(e.clientX); if (drag) setDrag([drag[0], i]); else setHi(i); }}
        onPointerUp={() => { if (drag && Math.abs(drag[1] - drag[0]) >= 3) setZoom([Math.min(...drag), Math.max(...drag)]); setDrag(null); }}
        onPointerLeave={() => { setHi(null); setDrag(null); }}
        onDoubleClick={() => setZoom(null)}>
        <defs>
          <clipPath id={`clip${uid}`}><rect x={LPL} y={LPT} width={LW - LPL - LPR} height={LH - LPT - LPB} /></clipPath>
          {lines.map((l) => (
            <linearGradient key={l.id} id={`g${uid}${l.id}`} x1="0" x2="0" y1="0" y2="1">
              <stop offset="0" stopColor={l.color} stopOpacity=".28" /><stop offset="1" stopColor={l.color} stopOpacity="0" />
            </linearGradient>
          ))}
        </defs>
        {[0, 25, 50, 75, 100].map((g) => (
          <g key={g}>
            <line x1={LPL} x2={LW - LPR} y1={y(g)} y2={y(g)} className="stroke-line2" />
            <text x={LPL - 6} y={y(g) + 4} textAnchor="end" className="fill-ink4 text-[11px]">{g}</text>
          </g>
        ))}
        {ticks.map((i) => (
          <text key={i} x={x(i)} y={LH - 8} textAnchor={x(i) > LW - 34 ? "end" : "middle"} className="fill-ink4 text-[11px]">
            {weekLabel(weeks[i])}</text>
        ))}
        <g clipPath={`url(#clip${uid})`}>
          <rect x={x(hist - 1)} y={LPT} width={Math.max(0, LW - LPR - x(hist - 1))} height={LH - LPT - LPB} className="fill-accent-soft" />
          <line x1={x(hist - 1)} x2={x(hist - 1)} y1={LPT} y2={LH - LPB} className="stroke-accent/40" strokeDasharray="4 4" />
          {one?.band && (
            <path fill={one.color} opacity=".16" d={area<[number, number]>().x((_, k) => x(hist + k)).y0((b) => y(b[0])).y1((b) => y(b[1]))
              .curve(curveMonotoneX)(one.band) ?? ""} />
          )}
          {lines.map((l, k) => (
            <g key={l.id}>
              {one && <path d={area<number>().x((_, i) => x(i)).y0(y(0)).y1((v) => y(v)).curve(curveMonotoneX)(l.values.slice(0, hist)) ?? ""}
                fill={`url(#g${uid}${l.id})`} />}
              <motion.path d={gen(l.values.slice(0, hist)) ?? ""} fill="none" stroke={l.color} strokeWidth="2.8" strokeLinecap="round"
                initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.1, delay: k * 0.12, ease: "easeOut" }} />
              <motion.path fill="none" stroke={l.color} strokeWidth="2.8" strokeDasharray="5 5" strokeLinecap="round"
                d={line<number>().x((_, i) => x(hist - 1 + i)).y((v) => y(v)).curve(curveMonotoneX)(l.values.slice(hist - 1)) ?? ""}
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1 + k * 0.12 }} />
              <circle cx={x(hist - 1)} cy={y(l.values[hist - 1])} r="4.5" fill={l.color} stroke="var(--surface)" strokeWidth="2" />
            </g>
          ))}
          {sel && <rect x={x(sel[0])} y={LPT} width={Math.max(1, x(sel[1]) - x(sel[0]))} height={LH - LPT - LPB} className="fill-accent/15" />}
        </g>
        {hi !== null && !drag && (
          <g>
            <line x1={x(hi)} x2={x(hi)} y1={LPT} y2={LH - LPB} className="stroke-ink4" />
            {lines.map((l) => <circle key={l.id} cx={x(hi)} cy={y(l.values[hi])} r="4" fill="var(--surface)" stroke={l.color} strokeWidth="2.2" />)}
          </g>
        )}
      </svg>
      {zoom && (
        <button type="button" onClick={() => setZoom(null)}
          className="absolute right-1 top-0 rounded border border-line bg-card px-2 py-0.5 text-[11px] font-semibold text-accent">Reset zoom</button>
      )}
      {hi !== null && !drag && (
        <div className="pointer-events-none absolute top-1 z-10 -translate-x-1/2 rounded-md bg-[var(--tip-bg)] px-3 py-2 text-[12px] text-[var(--tip-fg)] shadow-lg"
          style={{ left: `${Math.min(86, Math.max(14, (x(hi) / LW) * 100))}%` }}>
          <b className="block">{hi >= hist ? "Forecast · " : ""}Week of {weekLabel(weeks[hi])}</b>
          {lines.map((l) => (
            <span key={l.id} className="block opacity-80"><i className="mr-1.5 inline-block size-2 rounded-sm" style={{ background: l.color }} />
              {l.label}: {Math.round(l.values[hi])}</span>
          ))}
        </div>
      )}
      <p className="mt-1 text-[11px] text-ink4">Drag to zoom · double-click to reset</p>
    </div>
  );
}

export function Spark({ values, hist, color }: { values: number[]; hist: number; color: string }) {
  const W = 92, H = 26, n = values.length;
  const x = (i: number) => (i / (n - 1)) * (W - 2) + 1;
  const y = (v: number) => H - 3 - (v / 100) * (H - 6);
  const d = (a: number, b: number) => values.slice(a, b + 1)
    .map((v, k) => `${k ? "L" : "M"}${x(a + k).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} aria-hidden="true">
      <path d={d(0, hist - 1)} fill="none" stroke={color} strokeWidth="1.8" />
      <path d={d(hist - 1, n - 1)} fill="none" stroke={color} strokeWidth="1.8" strokeDasharray="3 3" opacity=".7" />
      <circle cx={x(hist - 1)} cy={y(values[hist - 1])} r="2.6" fill={color} />
    </svg>
  );
}

// Lifecycle curve with a marker at the trend's stage.
export function LifecycleStrip({ trend }: { trend: Trend }) {
  const W = 300, H = 92;
  const pts = Array.from({ length: 41 }, (_, i) => {
    const t = i / 40;
    return [10 + t * (W - 20), H - 22 - Math.sin(Math.PI * Math.pow(t, 0.85)) * (H - 40)] as const;
  });
  const d = pts.map(([px, py], i) => `${i ? "L" : "M"}${px.toFixed(1)} ${py.toFixed(1)}`).join(" ");
  const [mx, my] = pts[Math.round(trend.lifecycle_pos * 40)];
  const stages: Life[] = ["emerging", "growth", "peak", "mature", "decline"];
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="block h-auto w-full" role="img" aria-label={`Lifecycle stage: ${LIFE_LABEL[trend.life]}`}>
      <path d={d} fill="none" className="stroke-line" strokeWidth="3" strokeLinecap="round" />
      {stages.map((s, i) => (
        <text key={s} x={10 + ((i + 0.5) / 5) * (W - 20)} y={H - 4} textAnchor="middle"
          className={s === trend.life ? "fill-ink text-[11px] font-bold" : "fill-ink4 text-[11px]"}>{LIFE_LABEL[s]}</text>
      ))}
      <motion.circle r="8" fill={LIFE_COLOR[trend.life]} stroke="var(--surface)" strokeWidth="2.5"
        initial={{ cx: 10, cy: pts[0][1] }} animate={{ cx: mx, cy: my }} transition={{ type: "spring", stiffness: 90, damping: 16, delay: 0.3 }} />
    </svg>
  );
}
