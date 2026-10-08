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

import { animate, motion } from "motion/react";
import { Star } from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Bar, Btn, Card, CardTitle, LifePill, Momentum, Tag } from "@/components";
import { cn } from "@/lib/cn";
import {
  LIFE_COLOR, METRIC_LABEL, opportunity, weekLabel,
  type Metric, type Trend, type TrendsState,
} from "@/lib/trends";
import { Garment } from "./Garment";
import { LifecycleStrip, LineChart, Spark, type Line } from "./Charts";
import { kindFor, Texture } from "./Texture";

export const SERIES_COLORS = ["#1a73e8", "#ea4335", "#34a853"];

function luminance(hex: string): number {
  const v = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2];
}

function CountUp({ to }: { to: number }) {
  const [v, setV] = useState(0);
  useEffect(() => {
    const c = animate(0, to, { duration: 0.9, ease: "easeOut", onUpdate: (x) => setV(Math.round(x)) });
    return () => c.stop();
  }, [to]);
  return <>{v}</>;
}

const rise = { initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 } };

// ---------------------------------------------------------------------------
// Ranked list
// ---------------------------------------------------------------------------

type SortKey = "strength" | "momentum" | "coverage" | "opportunity";
const COLS = "grid-cols-[26px_minmax(0,1fr)_62px_62px_32px] md:grid-cols-[28px_minmax(0,2.2fr)_72px_72px_104px_minmax(90px,1fr)_52px_32px]";

export function ListView({ state, trends, matches, board, cmp, brand, onOpen, onBoard, onCmp }: {
  state: TrendsState; trends: Trend[]; matches: Set<string>; board: string[]; cmp: string[];
  brand: string; onOpen: (id: string) => void; onBoard: (id: string) => void; onCmp: (id: string) => void;
}) {
  const [sort, setSort] = useState<SortKey>("opportunity");
  const rows = useMemo(() => {
    const val = (t: Trend) => sort === "opportunity" ? opportunity(t) : sort === "coverage" ? -t.coverage : t[sort];
    return trends.filter((t) => matches.has(t.id)).sort((a, b) => val(b) - val(a));
  }, [trends, matches, sort]);
  const head = (k: SortKey, label: string, cls = "") => (
    <button type="button" onClick={() => setSort(k)}
      className={cn("text-right text-[10.5px] font-bold uppercase tracking-wider", sort === k ? "text-accent" : "text-ink3 hover:text-ink", cls)}>
      {label}{sort === k ? " ↓" : ""}
    </button>
  );
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-card shadow-[var(--shadow)]" role="table" aria-label="Trends">
      <div className={cn("grid items-center gap-2 border-b border-line bg-paper px-3 py-2", COLS)} role="row">
        <span /><span className="text-[10.5px] font-bold uppercase tracking-wider text-ink3">Trend</span>
        {head("strength", "Strength")}{head("momentum", "4-week")}
        <span className="text-[10.5px] font-bold uppercase tracking-wider text-ink3 max-md:hidden">Demand + forecast</span>
        {head("coverage", "Coverage", "max-md:hidden text-left")}{head("opportunity", "Gap", "max-md:hidden")}<span className="max-md:hidden" />
      </div>
      {rows.length === 0 && <p className="p-6 text-[13px] text-ink3">No trends match these filters.</p>}
      {rows.map((t, i) => (
        <motion.div key={t.id} {...rise} transition={{ delay: Math.min(i, 14) * 0.025 }} role="row"
          className={cn("grid items-center gap-2 border-t border-line2 px-3 py-2.5 hover:bg-paper/70", COLS)}>
          <label className="flex justify-center" title="Add to comparison">
            <input type="checkbox" className="size-4 accent-[var(--blue-700)]" checked={cmp.includes(t.id)}
              onChange={() => onCmp(t.id)} aria-label={`Compare ${t.name}`} />
          </label>
          <button type="button" onClick={() => onOpen(t.id)} className="min-w-0 text-left">
            <b className="block truncate font-serif text-[17px] font-medium leading-tight">{t.name}</b>
            <span className="flex items-center gap-2 text-[11.5px] text-ink3"><LifePill life={t.life} />{state.types[t.type]}
              {brand && <span>· fit {t.fit[brand]}</span>}</span>
          </button>
          <span className="text-right font-serif text-[20px] font-medium tabular-nums">{t.strength}</span>
          <span className="text-right"><Momentum v={t.momentum} /></span>
          <span className="max-md:hidden"><Spark values={t.series.overall} hist={state.hist} color={LIFE_COLOR[t.life]} /></span>
          <span className="flex items-center gap-2 max-md:hidden"><Bar value={t.coverage} />
            <em className="min-w-8 text-right text-[12.5px] not-italic text-ink2">{t.coverage}%</em></span>
          <span className={cn("text-right font-semibold tabular-nums max-md:hidden", opportunity(t) >= 30 ? "text-accent" : "text-ink3")}>{opportunity(t)}</span>
          <button type="button" onClick={() => onBoard(t.id)} aria-pressed={board.includes(t.id)}
            aria-label={board.includes(t.id) ? "Remove from board" : "Add to board"} className="justify-self-center">
            <Star size={18} className={board.includes(t.id) ? "fill-warn text-warn" : "text-ink4 hover:text-warn"} />
          </button>
        </motion.div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Detail: a poster header tinted by the trend's own palette, then the evidence.
// ---------------------------------------------------------------------------

export function Detail({ state, trend, metric, onMetric, board, onBoard, onBack, onAsk, onCmp, origin }: {
  state: TrendsState; trend: Trend; metric: Metric; onMetric: (m: Metric) => void; board: string[];
  onBoard: (id: string) => void; onBack: () => void; onAsk: (prompt: string) => void; onCmp: (id: string) => void;
  /** Where the user clicked (viewport px): the poster opens as a circle growing from there. */
  origin?: { x: number; y: number } | null;
}) {
  const recs = state.recs[trend.id] ?? [];
  const [c1, c2, c3] = trend.dna.palette.map((p) => p.hex);
  const dark = luminance(c1) < 0.4;
  const ox = origin ? Math.round((origin.x / Math.max(1, window.innerWidth)) * 100) : 20;
  const oy = origin ? Math.min(70, Math.round(origin.y / 8)) : 40;
  const tex = kindFor(trend.dna.fabrics);
  const ink = dark ? "#ffffff" : "#221e1a";
  const line: Line = { id: trend.id, label: METRIC_LABEL[metric], color: LIFE_COLOR[trend.life],
    values: trend.series[metric], band: metric === "overall" ? trend.band : undefined };
  const topCh = [...trend.channels].sort((a, b) => b.value - a.value)[0];
  const inBoard = board.includes(trend.id);
  const brandFit = state.brands.map((b) => ({ ...b, v: trend.fit[b.id] })).sort((a, b) => b.v - a.v);
  const stats: [string, ReactNode][] = [
    ["Strength", <CountUp key="s" to={trend.strength} />],
    ["4-week", `${trend.momentum > 0 ? "+" : ""}${trend.momentum}`],
    ["Coverage", <span key="c"><CountUp to={trend.coverage} />%</span>],
    ["Gap score", <CountUp key="g" to={opportunity(trend)} />],
    ["Expected peak", weekLabel(trend.peak_week)],
  ];
  return (
    <div className="space-y-4">
      <button type="button" onClick={onBack} className="text-[13px] font-semibold text-accent">← All trends</button>

      <motion.header className="relative overflow-hidden rounded-2xl p-6 md:p-8"
        initial={{ clipPath: `circle(0% at ${ox}% ${oy}%)` }} animate={{ clipPath: `circle(150% at ${ox}% ${oy}%)` }}
        transition={{ duration: 0.75, ease: [0.22, 1, 0.36, 1] }}
        style={{ background: `linear-gradient(118deg, ${c1} 0%, ${c1} 52%, ${c2} 135%)`, color: ink }}>
        <Texture kind={tex} opacity={0.13} />
        <motion.div className="pointer-events-none absolute -bottom-6 -right-4 opacity-95"
          initial={{ opacity: 0, x: 40, rotate: 8 }} animate={{ opacity: 0.95, x: 0, rotate: -6 }}
          transition={{ type: "spring", stiffness: 70, damping: 14, delay: 0.1 }}>
          <Garment shape={trend.dna.shape} color={c3 ?? c2} size={230} label="" />
        </motion.div>
        <p className="text-[11px] font-bold uppercase tracking-[.16em] opacity-80">
          {state.types[trend.type]} trend · {trend.life}</p>
        <h2 className="mt-1 max-w-[70%] font-serif text-[clamp(34px,7vw,56px)] font-medium leading-[1.02] tracking-tight">{trend.name}</h2>
        <p className="mt-3 max-w-[62%] text-[14px] leading-snug opacity-90">{trend.quick_read}</p>
        <dl className="relative mt-6 grid max-w-[78%] grid-cols-3 gap-x-4 gap-y-3 border-t pt-4 md:grid-cols-5"
          style={{ borderColor: `${ink}33` }}>
          {stats.map(([k, v]) => (
            <div key={k}><dt className="text-[10px] font-bold uppercase tracking-[.12em] opacity-70">{k}</dt>
              <dd className="font-serif text-[26px] font-medium leading-tight tabular-nums">{v}</dd></div>
          ))}
        </dl>
      </motion.header>

      <div className="flex flex-wrap gap-2">
        <Btn variant="primary" onClick={() => onAsk(`Recommend actions for ${trend.name}`)}>Ask agent: recommend actions</Btn>
        <Btn onClick={() => onAsk(`What is driving ${trend.name}, and will it last?`)}>What's driving it?</Btn>
        <Btn onClick={() => onCmp(trend.id)}>Compare…</Btn>
        <Btn on={inBoard} onClick={() => onBoard(trend.id)}>
          <Star size={14} className={inBoard ? "fill-current" : ""} />{inBoard ? "On board" : "Add to board"}</Btn>
      </div>

      <Card className="border-accent/30 bg-accent-soft/60">
        <CardTitle aside={<Tag>Agent</Tag>}>Recommended actions</CardTitle>
        {recs.length === 0 ? (
          <p className="text-[13px] text-ink3">No recommendations yet. The agent writes them here from the data on this page.</p>
        ) : (
          <ul className="divide-y divide-line">
            {recs.map((r, i) => (
              <motion.li key={i} {...rise} transition={{ delay: 0.15 + i * 0.1 }} className="flex gap-3 py-3 first:pt-0 last:pb-0">
                <span className={cn("h-fit min-w-16 rounded px-2 py-0.5 text-center text-[10px] font-extrabold uppercase tracking-wider",
                  r.priority === "high" ? "bg-bad-soft text-bad" : r.priority === "medium" ? "bg-warn-soft text-warn" : "bg-line2 text-ink3")}>{r.priority}</span>
                <div><b className="font-serif text-[16px] font-medium">{r.action}</b>
                  <p className="text-[13px] text-ink2">{r.why}</p>
                  <small className="text-[11.5px] text-ink3">{r.owner} · {r.timing}</small></div>
              </motion.li>
            ))}
          </ul>
        )}
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="md:col-span-2">
          <CardTitle aside={
            <div className="flex flex-wrap gap-1" role="tablist" aria-label="Signal source">
              {(Object.keys(METRIC_LABEL) as Metric[]).map((m) => (
                <button key={m} type="button" role="tab" aria-selected={m === metric} onClick={() => onMetric(m)}
                  className={cn("rounded px-2.5 py-1 text-[12px] font-semibold", m === metric ? "bg-accent text-[var(--on-accent)]" : "text-ink3 hover:text-ink")}>{METRIC_LABEL[m]}</button>
              ))}
            </div>}>Demand index &amp; 12-week forecast</CardTitle>
          <LineChart lines={[line]} state={state} />
          <p className="mt-1 text-[11.5px] text-ink3">Solid = observed, dashed = forecast{metric === "overall" ? " with a widening confidence band" : ""}.
            {topCh && ` ${topCh.label} is the strongest channel (${topCh.value}).`}</p>
        </Card>

        <Card>
          <CardTitle>Lifecycle</CardTitle>
          <LifecycleStrip trend={trend} />
          <div className="mt-5" />
          <CardTitle>Channel signals</CardTitle>
          <ul className="space-y-1.5">
            {trend.channels.map((c) => (
              <li key={c.id} className="grid grid-cols-[78px_1fr_28px_34px] items-center gap-2 text-[13px]">
                <span className="text-ink2">{c.label}</span><Bar value={c.value} /><b className="tabular-nums">{c.value}</b>
                <em className={cn("text-[11.5px] font-bold not-italic", c.delta >= 0 ? "text-good" : "text-bad")}>{c.delta >= 0 ? "+" : ""}{c.delta}</em>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <CardTitle>Assortment coverage</CardTitle>
          <div className="mb-2 flex items-baseline gap-3"><b className="font-serif text-[40px] font-medium leading-none tabular-nums">{trend.coverage}%</b>
            <span className="text-[13px] text-ink3">of demand covered by the current catalog</span></div>
          <Bar value={trend.coverage} tone={trend.coverage < 45 ? "warn" : "accent"} />
          <p className="mt-2 text-[12px] text-ink3">{trend.strength >= 60 && trend.coverage < 45
            ? "Whitespace: strong demand with a thin assortment." : trend.coverage >= 65 && trend.life !== "peak" && trend.life !== "growth"
              ? "Heavily covered while demand fades." : "Coverage is in line with demand."}</p>
          <div className="mt-5" />
          <CardTitle>Brand fit</CardTitle>
          <ul className="space-y-1.5">
            {brandFit.map((b) => (
              <li key={b.id} className="grid grid-cols-[78px_1fr_28px] items-center gap-2 text-[13px]">
                <span className="text-ink2">{b.name.replace("Cymbal ", "")}</span><Bar value={b.v} /><b className="tabular-nums">{b.v}</b></li>
            ))}
          </ul>
        </Card>

        <Card className="md:col-span-2">
          <CardTitle>Visual DNA</CardTitle>
          <div className="grid grid-cols-3 gap-3">
            {trend.dna.palette.map((p, i) => (
              <motion.div key={p.hex} {...rise} transition={{ delay: i * 0.08 }}
                className="relative flex h-28 flex-col justify-end overflow-hidden rounded-xl p-3 md:h-36"
                style={{ background: p.hex, color: luminance(p.hex) < 0.4 ? "#fff" : "#221e1a" }}>
                <Texture kind={tex} opacity={0.18} />
                <b className="relative font-serif text-[16px] font-medium">{p.name}</b><span className="relative text-[11px] uppercase tracking-wider opacity-75">{p.hex}</span>
              </motion.div>
            ))}
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {([["Silhouettes", trend.dna.silhouettes], ["Fabrics", trend.dna.fabrics], ["Mood", trend.dna.moods]] as [string, string[]][]).map(([label, items]) => (
              <div key={label}><small className="mb-1.5 block text-[10.5px] font-bold uppercase tracking-wider text-ink3">{label}</small>
                <div className="flex flex-wrap gap-1.5">{items.map((t) => (
                  <span key={t} className="rounded border border-line bg-paper px-2.5 py-0.5 font-serif text-[14px] ">{t}</span>))}</div></div>
            ))}
          </div>
        </Card>

        <Card>
          <CardTitle>Cultural drivers</CardTitle>
          <ul className="space-y-1.5 text-[13.5px]">{trend.drivers.map((d) => (
            <li key={d} className="flex gap-2"><span className="mt-2 size-1.5 shrink-0 rounded-full bg-accent" />{d}</li>))}</ul>
        </Card>
        <Card>
          <CardTitle aside={<Tag tone="neutral">Illustrative</Tag>}>Sources</CardTitle>
          <ul className="divide-y divide-line2">{trend.articles.map((a) => (
            <li key={a.title} className="py-2 first:pt-0"><b className="block font-serif text-[15px] font-medium leading-snug">{a.title}</b>
              <span className="text-[11.5px] text-ink3">{a.source} · {weekLabel(a.date)}</span></li>))}</ul>
        </Card>

        <Card className="md:col-span-2">
          <CardTitle>Matching products in the catalog</CardTitle>
          <div className="grid grid-cols-[repeat(auto-fill,minmax(168px,1fr))] gap-3">
            {trend.products.map((m, i) => {
              const p = state.products[m.sku];
              return (
                <motion.div key={m.sku} {...rise} transition={{ delay: i * 0.08 }} className="rounded-xl border border-line bg-paper p-3">
                  <div className="mb-2 flex justify-center rounded" style={{ background: `${p.hex}1f` }}><Garment shape={p.shape} color={p.hex} size={74} label={p.name} /></div>
                  <b className="block font-serif text-[15px] font-medium leading-tight">{p.name}</b>
                  <span className="text-[11.5px] text-ink3">{p.brand === "kids" ? "Kids" : `Cymbal ${p.brand[0].toUpperCase()}${p.brand.slice(1)}`} · ${p.price}</span>
                  <span className="mt-1 block text-[12px] font-bold text-good">{m.match}% match</span>
                  <div className="mt-1"><Bar value={p.sell_through} tone="good" /></div>
                  <em className="text-[11px] not-italic text-ink3">{p.sell_through}% sell-through · {p.weeks_cover}w cover</em>
                </motion.div>
              );
            })}
            {trend.coverage < 45 && (
              <button type="button" onClick={() => onAsk(`Size the assortment gap for ${trend.name}`)}
                className="flex flex-col items-center justify-center gap-1 rounded-md border-[1.5px] border-dashed border-accent/40 bg-accent-soft p-3 text-center hover:bg-accent-soft/60">
                <span className="text-[26px] leading-none text-accent">＋</span><b className="font-serif text-[15px]">Coverage gap</b>
                <span className="text-[12px] text-ink2">{100 - trend.coverage}% of demand has no matching product. Ask the agent to size it.</span>
              </button>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Compare
// ---------------------------------------------------------------------------

function Empty({ title, text, cta, onClick }: { title: string; text: string; cta: string; onClick: () => void }) {
  return (
    <div className="px-4 py-14 text-center">
      <h3 className="font-serif text-[26px] font-medium">{title}</h3>
      <p className="mx-auto mt-1 max-w-md text-[13.5px] text-ink3">{text}</p>
      <Btn variant="primary" className="mt-4" onClick={onClick}>{cta}</Btn>
    </div>
  );
}

export function Compare({ state, ids, onOpen, onRemove, onAsk }: {
  state: TrendsState; ids: string[]; onOpen: (id: string) => void; onRemove: (id: string) => void; onAsk: (p: string) => void;
}) {
  const ts = ids.map((i) => state.trends.find((t) => t.id === i)).filter(Boolean) as Trend[];
  if (ts.length < 2) {
    return <Empty title="Compare trends" text="Tick two or three trends in the list, or ask the agent to compare them."
      cta="Ask agent: compare the top whitespace trends" onClick={() => onAsk("Compare the two strongest whitespace trends")} />;
  }
  const lines: Line[] = ts.map((t, i) => ({ id: t.id, label: t.name, color: SERIES_COLORS[i], values: t.series.overall }));
  const rows: [string, (t: Trend) => ReactNode][] = [
    ["Lifecycle", (t) => <LifePill life={t.life} />],
    ["Strength", (t) => <b className="font-serif text-[20px]">{t.strength}</b>],
    ["4-week momentum", (t) => <Momentum v={t.momentum} />],
    ["Forecast (12 wks)", (t) => <b>{Math.round(t.series.overall[t.series.overall.length - 1])}</b>],
    ["Coverage", (t) => <span className="flex items-center gap-2"><Bar value={t.coverage} /><em className="not-italic">{t.coverage}%</em></span>],
    ["Opportunity gap", (t) => <b>{opportunity(t)}</b>],
    ["Strongest channel", (t) => [...t.channels].sort((a, b) => b.value - a.value)[0].label],
    ["Best-fit brand", (t) => { const b = state.brands.reduce((m, x) => t.fit[x.id] > t.fit[m.id] ? x : m); return `${b.name.replace("Cymbal ", "")} (${t.fit[b.id]})`; }],
  ];
  return (
    <div className="space-y-4">
      <Card>
        <CardTitle aside={<div className="flex flex-wrap gap-3 text-[12px] text-ink2">{ts.map((t, i) => (
          <span key={t.id} className="inline-flex items-center gap-1.5"><i className="size-2.5 rounded-sm" style={{ background: SERIES_COLORS[i] }} />{t.name}</span>))}</div>}>
          Demand index, side by side</CardTitle>
        <LineChart lines={lines} state={state} />
      </Card>
      <Card>
        <table className="w-full table-fixed border-collapse text-[13px]">
          <thead><tr><th className="w-[88px] md:w-[150px]" />{ts.map((t, i) => (
            <th key={t.id} className="px-2 pb-3 text-left align-bottom font-serif text-[16px] font-medium">
              <button type="button" onClick={() => onOpen(t.id)} className="text-left">
                <i className="mr-1.5 inline-block size-2.5 rounded-sm" style={{ background: SERIES_COLORS[i] }} />{t.name}</button>
              <button type="button" aria-label={`Remove ${t.name}`} onClick={() => onRemove(t.id)} className="ml-1 text-ink4 hover:text-bad">×</button>
            </th>))}</tr></thead>
          <tbody>{rows.map(([label, f]) => (
            <tr key={label} className="border-t border-line2"><th className="py-2.5 pr-2 text-left text-[12px] font-semibold text-ink3">{label}</th>
              {ts.map((t) => <td key={t.id} className="px-2 py-2.5 [overflow-wrap:anywhere]">{f(t)}</td>)}</tr>))}</tbody>
        </table>
        <div className="mt-4"><Btn variant="primary" onClick={() => onAsk(`Which should I buy into first: ${ts.map((t) => t.name).join(", ")}?`)}>
          Ask agent: which first?</Btn></div>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Board
// ---------------------------------------------------------------------------

export function Board({ state, ids, onOpen, onRemove, onAsk }: {
  state: TrendsState; ids: string[]; onOpen: (id: string) => void; onRemove: (id: string) => void; onAsk: (p: string) => void;
}) {
  const ts = ids.map((i) => state.trends.find((t) => t.id === i)).filter(Boolean) as Trend[];
  if (ts.length === 0) {
    return <Empty title="Your board is empty" text="Star trends in the list or the detail view to shortlist them, or ask the agent to start one."
      cta="Ask agent: start my board" onClick={() => onAsk("Start my board with the three best whitespace trends")} />;
  }
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-[repeat(auto-fill,minmax(250px,1fr))] gap-3">
        {ts.map((t, i) => {
          const recs = state.recs[t.id] ?? [];
          const c = t.dna.palette[0].hex;
          return (
            <motion.article key={t.id} {...rise} transition={{ delay: i * 0.07 }} className="relative overflow-hidden rounded-xl border border-line bg-card shadow-[var(--shadow)]">
              <div className="h-1.5" style={{ background: c }} />
              <button type="button" aria-label={`Remove ${t.name}`} onClick={() => onRemove(t.id)} className="absolute right-2 top-3 text-ink4 hover:text-bad">×</button>
              <div className="p-4">
                <button type="button" onClick={() => onOpen(t.id)} className="flex items-center gap-3 text-left">
                  <Garment shape={t.dna.shape} color={c} size={48} label={t.name} />
                  <span><b className="block font-serif text-[18px] font-medium leading-tight">{t.name}</b><LifePill life={t.life} /></span>
                </button>
                <div className="my-3 flex gap-5 text-[11px] uppercase tracking-wider text-ink3">
                  <span><b className="block font-serif text-[22px] normal-case text-ink">{t.strength}</b>strength</span>
                  <span><Momentum v={t.momentum} /><span className="block">4-week</span></span>
                  <span><b className="block font-serif text-[22px] normal-case text-ink">{t.coverage}%</b>covered</span>
                </div>
                {recs.length > 0
                  ? <ul className="space-y-1 border-t border-line2 pt-2 text-[12.5px]">{recs.slice(0, 2).map((r, k) => (
                    <li key={k} className="flex gap-2"><span className={cn("h-fit rounded px-1.5 text-[9.5px] font-extrabold uppercase",
                      r.priority === "high" ? "bg-bad-soft text-bad" : r.priority === "medium" ? "bg-warn-soft text-warn" : "bg-line2 text-ink3")}>{r.priority}</span>{r.action}</li>))}</ul>
                  : <p className="border-t border-line2 pt-2 text-[12px] text-ink3">No actions yet.</p>}
              </div>
            </motion.article>
          );
        })}
      </div>
      <div className="flex flex-wrap gap-2">
        <Btn variant="primary" onClick={() => onAsk("Recommend actions for each trend on my board")}>Ask agent: recommend actions for my board</Btn>
        <Btn onClick={() => onAsk("What am I missing from my board?")}>What am I missing?</Btn>
      </div>
    </div>
  );
}
