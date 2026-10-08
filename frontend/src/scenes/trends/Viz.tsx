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

import { scaleLinear } from "d3-scale";
import { area, curveBasis, line } from "d3-shape";
import { motion } from "motion/react";
import { useMemo, useState } from "react";
import { Tip } from "@/components";
import { cn } from "@/lib/cn";
import { LIFE_COLOR, LIFE_LABEL, opportunity, weekLabel, type TrendsState } from "@/lib/trends";

// ---------------------------------------------------------------------------
// Heatmap: every trend against every brand. Cell color = brand fit; the bar = assortment coverage.
// Sorted by opportunity, or by one brand's fit (click a brand header).
// ---------------------------------------------------------------------------

export function Heatmap({ state, matches, highlight, onOpen }: {
  state: TrendsState; matches: Set<string>; highlight: string[]; onOpen: (id: string) => void;
}) {
  const [by, setBy] = useState<string>("gap");
  const rows = useMemo(() => state.trends.filter((t) => matches.has(t.id))
    .sort((a, b) => by === "gap" ? opportunity(b) - opportunity(a) : b.fit[by] - a.fit[by]), [state.trends, matches, by]);
  const cols = "grid-cols-[minmax(140px,1.7fr)_repeat(4,minmax(44px,1fr))_minmax(70px,1fr)]";
  const cell = (v: number) => ({
    background: `color-mix(in srgb, var(--blue-600) ${Math.round(v * 0.92)}%, var(--surface))`,
    color: v >= 55 ? "var(--on-accent)" : "var(--ink)",
  });
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-card p-3 shadow-[var(--shadow)]">
      <div className={cn("grid items-end gap-1.5 px-1 pb-2", cols)}>
        <button type="button" onClick={() => setBy("gap")}
          className={cn("text-left text-[11px] font-medium uppercase tracking-wider", by === "gap" ? "text-accent" : "text-ink3")}>
          Trend · by gap</button>
        {state.brands.map((b) => (
          <button key={b.id} type="button" onClick={() => setBy(b.id)} title={`Sort by ${b.name} fit`}
            className={cn("text-center text-[11px] font-medium uppercase tracking-wider", by === b.id ? "text-accent" : "text-ink3 hover:text-ink")}>
            {b.name.replace("Cymbal ", "")}{by === b.id ? " ↓" : ""}</button>
        ))}
        <span className="text-center text-[11px] font-medium uppercase tracking-wider text-ink3">Coverage</span>
      </div>
      <div className="space-y-1.5">
        {rows.map((t, i) => (
          <motion.div key={t.id} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: Math.min(i, 16) * 0.02 }}
            className={cn("grid items-center gap-1.5", cols, highlight.includes(t.id) && "rounded-lg ring-2 ring-accent/40")}>
            <button type="button" onClick={() => onOpen(t.id)} className="flex min-w-0 items-center gap-2 text-left">
              <i className="size-2.5 shrink-0 rounded-full" style={{ background: LIFE_COLOR[t.life] }} />
              <span className="truncate font-serif text-[14px] font-medium">{t.name}</span>
            </button>
            {state.brands.map((b) => (
              <Tip key={b.id} content={<div><b>{t.name}</b><div className="opacity-80">{b.name}: fit {t.fit[b.id]} · {t.coverage}% covered</div></div>}>
                <button type="button" onClick={() => onOpen(t.id)} style={cell(t.fit[b.id])}
                  className="h-8 rounded-lg text-[13px] font-medium tabular-nums transition-transform hover:scale-105">{t.fit[b.id]}</button>
              </Tip>
            ))}
            <span className="flex items-center gap-1.5">
              <span className="block h-2 flex-1 overflow-hidden rounded-full bg-line2">
                <i className={cn("block h-full rounded-full", t.coverage < 45 ? "bg-[#f9ab00]" : "bg-accent")} style={{ width: `${t.coverage}%` }} /></span>
              <em className="w-8 text-right text-[12px] not-italic text-ink3 tabular-nums">{t.coverage}%</em>
            </span>
          </motion.div>
        ))}
        {rows.length === 0 && <p className="p-6 text-[13px] text-ink3">No trends match these filters.</p>}
      </div>
      <p className="mt-3 px-1 text-[11.5px] text-ink3">Darker = stronger fit for the brand. Amber coverage = thin assortment. Click a brand name to sort by it.</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Ridgeline timeline: every trend's demand curve, stacked and overlapping, sorted by when it peaks.
// ---------------------------------------------------------------------------

const TW = 700, LEFT = 168, RIGHT = 16, STEP = 28, AMP = 58, TOP = 30;

export function Timeline({ state, matches, highlight, onOpen }: {
  state: TrendsState; matches: Set<string>; highlight: string[]; onOpen: (id: string) => void;
}) {
  const [hover, setHover] = useState<string | null>(null);
  const n = state.weeks.length, hist = state.hist;
  const rows = useMemo(() => state.trends.filter((t) => matches.has(t.id))
    .map((t) => ({ t, peak: t.series.overall.reduce((m, v, i, a) => (v > a[m] ? i : m), 0) }))
    .sort((a, b) => a.peak - b.peak), [state.trends, matches]);
  const x = scaleLinear().domain([0, n - 1]).range([LEFT, TW - RIGHT]);
  const H = TOP + rows.length * STEP + AMP;
  const y0 = (i: number) => TOP + i * STEP + AMP;
  const gen = (i: number) => area<number>().x((_, k) => x(k)).y0(y0(i)).y1((v) => y0(i) - (v / 100) * AMP).curve(curveBasis);
  const top = (i: number) => line<number>().x((_, k) => x(k)).y((v) => y0(i) - (v / 100) * AMP).curve(curveBasis);
  const ticks = [0, 6, 12, 18, 25, 31, 37].filter((i) => i < n);

  return (
    <div className="overflow-hidden rounded-xl border border-line bg-card p-2 pb-3 shadow-[var(--shadow)]">
      <svg viewBox={`0 0 ${TW} ${H}`} className="block h-auto w-full" role="img" aria-label="Demand curves of every trend, ordered by peak week">
        <rect x={x(hist - 1)} y={TOP - 6} width={TW - RIGHT - x(hist - 1)} height={H - TOP + 6} className="fill-accent-soft" />
        <line x1={x(hist - 1)} x2={x(hist - 1)} y1={TOP - 6} y2={H} className="stroke-accent/50" strokeDasharray="4 4" />
        <text x={x(hist - 1) + 6} y={TOP + 4} className="fill-accent text-[11px] font-medium">Today · forecast →</text>
        {ticks.map((i) => <text key={i} x={x(i)} y={H - 4} textAnchor={x(i) > TW - 30 ? "end" : "middle"} className="fill-ink4 text-[10.5px]">{weekLabel(state.weeks[i])}</text>)}
        {rows.map(({ t, peak }, i) => {
          const dim = (hover && hover !== t.id) || (highlight.length > 0 && !highlight.includes(t.id));
          return (
            <Tip key={t.id} content={<div><b>{t.name}</b><div className="opacity-80">{LIFE_LABEL[t.life]} · peaks week of {weekLabel(state.weeks[peak])}</div>
              <div className="opacity-80">strength {t.strength} · {t.coverage}% covered</div></div>}>
              <motion.g role="button" tabIndex={0} className="cursor-pointer outline-none" initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: dim ? 0.25 : 1, y: 0 }} transition={{ delay: Math.min(i, 24) * 0.025 }}
                onMouseEnter={() => setHover(t.id)} onMouseLeave={() => setHover(null)} onClick={() => onOpen(t.id)}
                onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onOpen(t.id)} aria-label={`${t.name}, peaks week of ${weekLabel(state.weeks[peak])}`}>
                <path d={gen(i)(t.series.overall) ?? ""} fill={LIFE_COLOR[t.life]} fillOpacity=".78" />
                <path d={top(i)(t.series.overall) ?? ""} fill="none" stroke="var(--surface)" strokeWidth="1.6" />
                <circle cx={x(peak)} cy={y0(i) - (t.series.overall[peak] / 100) * AMP} r="3.5" fill="var(--surface)" stroke={LIFE_COLOR[t.life]} strokeWidth="2" />
                <text x={LEFT - 10} y={y0(i) - 3} textAnchor="end" className={cn("text-[12px]", hover === t.id ? "fill-ink font-medium" : "fill-ink2")}>{t.name}</text>
              </motion.g>
            </Tip>
          );
        })}
      </svg>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-2 pt-1 text-[11.5px] text-ink3">
        {(Object.keys(LIFE_LABEL) as (keyof typeof LIFE_COLOR)[]).map((l) => (
          <span key={l} className="inline-flex items-center gap-1.5"><i className="size-2.5 rounded-full" style={{ background: LIFE_COLOR[l] }} />{LIFE_LABEL[l]}</span>))}
        <span className="ml-auto">Ordered by peak week · dot = peak · click a curve to open it</span>
      </div>
    </div>
  );
}
