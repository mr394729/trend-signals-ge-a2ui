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

// The Trend Signals workspace (Gemini Enterprise Canvas side panel, one IFrameSrcdoc).
//
// Everything here is local and instant: tabs, filters, drill-down, board and comparison are React
// state over the data the server injected. The agent is reached only through `ask()`, which posts
// the canvas state with a prompt; the agent's reply arrives as a NEW surface that remounts this
// page with the state the agent chose (see lib/bridge.ts).

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { AlertTriangle, Command, Layers, Loader2, Moon, Search, Sparkles, Sun, TrendingUp, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { Palette } from "@/palette";
import { Pick, Segmented, Tag, TipProvider, ViewTabs } from "@/components";
import { cn } from "@/lib/cn";
import { onAction, sendAction } from "@/lib/bridge";
import {
  isAtRisk, isWhitespace, uiParams, weekLabel,
  type Filters, type Metric, type Trend, type TrendsState, type Ui, type ViewId,
} from "@/lib/trends";
import { OpportunityMap } from "./trends/Charts";
import { Board, Compare, Detail, ListView } from "./trends/Views";
import { Heatmap, Timeline } from "./trends/Viz";

type HomeView = "map" | "list" | "heatmap" | "timeline";
const HOMES: HomeView[] = ["map", "list", "heatmap", "timeline"];
type Focus = "" | "rising" | "whitespace" | "risk";
const FOCUS_LABEL: Record<Exclude<Focus, "">, string> = {
  rising: "Accelerating trends", whitespace: "Whitespace gaps", risk: "Assortment at risk",
};
const FOCUS_FN: Record<Exclude<Focus, "">, (t: Trend) => boolean> = {
  rising: (t) => t.momentum >= 5, whitespace: isWhitespace, risk: isAtRisk,
};
const BUSY_TIMEOUT_MS = 90_000;

export function TrendsScene({ state }: { state: TrendsState }) {
  const [ui, setUi] = useState<Ui>(state.ui);
  const [home, setHome] = useState<HomeView>(HOMES.includes(state.ui.view as HomeView) ? (state.ui.view as HomeView) : "map");
  const [focus, setFocus] = useState<Focus>("");
  const [note, setNote] = useState(state.note);
  const [hint, setHint] = useState("");
  const [origin, setOrigin] = useState<{ x: number; y: number } | null>(null);
  const [palette, setPalette] = useState(false);
  const [dark, setDark] = useState(false);
  const scroller = useRef<HTMLElement>(null); // the content region scrolls; the header stays put

  useEffect(() => { document.documentElement.dataset.theme = dark ? "dark" : "light"; }, [dark]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = /^(INPUT|TEXTAREA|SELECT)$/.test((e.target as HTMLElement)?.tagName ?? "");
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPalette((o) => !o); }
      else if (e.key === "/" && !typing) { e.preventDefault(); setPalette(true); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  const busy = useBusy();

  const trend = state.trends.find((t) => t.id === ui.sel) ?? null;
  const view: ViewId = ui.view === "detail" && !trend ? home : ui.view;

  const matches = useMemo(() => {
    const f = ui.f;
    const q = f.q.trim().toLowerCase();
    return new Set(state.trends.filter((t) =>
      (!f.type || t.type === f.type) && (!f.life || t.life === f.life)
      && (!f.brand || t.fit[f.brand] >= 50) && (!q || t.name.toLowerCase().includes(q))
      && (!focus || FOCUS_FN[focus](t)) && (ui.hl.length === 0 || ui.hl.includes(t.id))).map((t) => t.id));
  }, [state.trends, ui.f, ui.hl, focus]);

  // After the agent re-renders the same page, put the user back where they were.
  useEffect(() => {
    if (state.ui.sy > 0) scroller.current?.scrollTo({ top: state.ui.sy });
  }, [state.ui.sy]);

  const patch = (p: Partial<Ui>) => setUi((u) => ({ ...u, ...p }));
  const setFilter = (k: keyof Filters, v: string) => setUi((u) => ({ ...u, f: { ...u.f, [k]: v } }));
  const goto = (v: ViewId) => {
    if (HOMES.includes(v as HomeView)) setHome(v as HomeView);
    setHint("");
    patch({ view: v });
  };
  const open = (id: string, at?: { x: number; y: number }) => {
    setOrigin(at ?? null);
    patch({ view: "detail", sel: id });
    scroller.current?.scrollTo({ top: 0 });
  };
  const toggleBoard = (id: string) => setUi((u) => ({
    ...u, board: u.board.includes(id) ? u.board.filter((x) => x !== id) : [...u.board, id],
  }));
  const toggleCmp = (id: string) => setUi((u) => ({
    ...u, cmp: u.cmp.includes(id) ? u.cmp.filter((x) => x !== id) : [...u.cmp, id].slice(-3),
  }));
  const startCompare = (id: string) => {
    const next = ui.cmp.includes(id) ? ui.cmp : [...ui.cmp, id].slice(-3);
    if (next.length >= 2) patch({ cmp: next, view: "compare" });
    else {
      patch({ cmp: next, view: "list" });
      setHome("list");
      setHint(`Tick one more trend to compare with ${state.trends.find((t) => t.id === id)?.name}.`);
    }
  };

  const ask = (prompt: string) => {
    const text = prompt.trim();
    if (!text) return;
    sendAction({ action: "ask", prompt: text, data: uiParams(ui, scroller.current?.scrollTop ?? 0) });
  };

  const chips = chipsFor(view, trend, ui, state);
  const tab = view === "detail" ? home : view;
  const filterable = view === "map" || view === "list" || view === "heatmap" || view === "timeline";
  const k = state.kpis;
  const tiles: { id: Focus; n: number; label: string; tone: string; icon: ReactNode }[] = [
    { id: "", n: k.tracked, label: "Trends tracked", tone: "", icon: <Layers size={14} /> },
    { id: "rising", n: k.rising, label: "Accelerating", tone: "up", icon: <TrendingUp size={14} /> },
    { id: "whitespace", n: k.whitespace, label: "Whitespace gaps", tone: "gap", icon: <Sparkles size={14} /> },
    { id: "risk", n: k.at_risk, label: "Assortment at risk", tone: "risk", icon: <AlertTriangle size={14} /> },
  ];

  return (
    <TipProvider>
      <Palette open={palette} onOpenChange={setPalette} trends={state.trends} onOpenTrend={(id) => open(id)}
        onGoto={goto} onAsk={ask} questions={chips} />
      <div className="mx-auto flex h-dvh max-w-[1040px] flex-col px-4">
        <div className="shrink-0">

        <header className="flex items-end justify-between gap-4 pb-3 pt-2">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[.16em] text-accent">
              {state.retailer} · Trend signals · Week of {weekLabel(state.as_of)}</p>
            <h1 className="font-serif text-[34px] font-normal leading-none tracking-tight">Trend radar</h1>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <Tag tone="neutral">Illustrative data</Tag>
            <button type="button" onClick={() => setPalette(true)} aria-label="Search and jump" title="Search and jump (Ctrl/⌘ K or /)"
              className="inline-flex items-center gap-1.5 rounded-full border border-line px-2.5 py-1.5 text-[12px] text-ink3 hover:text-ink">
              <Command size={13} />K</button>
            <button type="button" onClick={() => setDark((d) => !d)} aria-label={dark ? "Switch to the light theme" : "Switch to the dark theme"}
              className="rounded-md border border-line p-1.5 text-ink3 hover:text-ink">{dark ? <Sun size={15} /> : <Moon size={15} />}</button>
            {busy && (
              <span role="status" className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent-soft px-3 py-1 text-[12.5px] text-accent">
                <Loader2 size={13} className="animate-spin" />Agent is working…</span>
            )}
          </div>
        </header>

        <div aria-hidden="true" className="h-[3px] rounded-full"
          style={{ background: "linear-gradient(90deg,#4285f4 0 25%,#ea4335 25% 50%,#fbbc04 50% 75%,#34a853 75% 100%)" }} />
        {view !== "detail" && (
          <div className="mb-3 mt-1 grid grid-cols-2 border-b border-line md:grid-cols-4" role="group" aria-label="Quick focus">
            {tiles.map((x, i) => (
              <button key={x.label} type="button" aria-pressed={Boolean(x.id) && focus === x.id}
                onClick={() => { if (x.id) { setFocus(focus === x.id ? "" : x.id); patch({ hl: [] }); if (view !== "list") goto("map"); } }}
                className={cn("flex flex-col items-start px-4 py-2.5 text-left transition-colors hover:bg-accent-soft/60",
                  i > 0 && "md:border-l md:border-line", i === 1 && "max-md:border-l max-md:border-line",
                  i > 1 && "max-md:border-t max-md:border-line", i === 3 && "max-md:border-l max-md:border-line",
                  Boolean(x.id) && focus === x.id && "bg-accent-soft")}>
                <b className={cn("font-serif text-[34px] font-semibold leading-none tabular-nums",
                  x.tone === "up" && "text-good", x.tone === "gap" && "text-accent", x.tone === "risk" && "text-bad")}>{x.n}</b>
                <span className="mt-1 inline-flex items-center gap-1.5 text-[10.5px] font-semibold uppercase tracking-[.08em] text-ink3">{x.icon}{x.label}</span>
              </button>
            ))}
          </div>
        )}

        <AnimatePresence>
          {note && (
            <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} role="status"
              className="mb-3 flex items-start gap-2.5 rounded-md border border-accent/25 bg-accent-soft px-3 py-2">
              <Tag>Agent</Tag><p className="flex-1 text-[13px] text-ink2">{note}</p>
              <button type="button" aria-label="Dismiss" onClick={() => setNote("")} className="text-ink3 hover:text-ink"><X size={15} /></button>
            </motion.div>
          )}
        </AnimatePresence>

        <ViewTabs value={tab} onChange={(v) => goto(v as ViewId)} items={[
          { value: "map", label: "Opportunity map" }, { value: "list", label: "Ranked list" },
          { value: "heatmap", label: "Brand fit" }, { value: "timeline", label: "Timeline" },
          { value: "compare", label: `Compare${ui.cmp.length ? ` (${ui.cmp.length})` : ""}` },
          { value: "board", label: `Board${ui.board.length ? ` (${ui.board.length})` : ""}` }]} />

        {filterable && (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Segmented label="Trend type" value={ui.f.type} onChange={(v) => setFilter("type", v)}
              options={[{ value: "", label: "All" }, ...Object.entries(state.types).map(([value, label]) => ({ value, label }))]} />
            <Pick label="Brand" value={ui.f.brand} onChange={(v) => setFilter("brand", v)} allLabel="All brands"
              options={state.brands.map((b) => ({ value: b.id, label: b.name }))} />
            <Pick label="Lifecycle" value={ui.f.life} onChange={(v) => setFilter("life", v)} allLabel="Any lifecycle"
              options={state.lifecycles.map((l) => ({ value: l, label: l[0].toUpperCase() + l.slice(1) }))} />
            <label className="relative">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-ink4" />
              <input type="search" placeholder="Search trends" aria-label="Search trends" value={ui.f.q}
                onChange={(e) => setFilter("q", e.target.value)}
                className="w-40 rounded-full border border-line bg-card py-1.5 pl-8 pr-2 text-[13px] outline-none focus:border-accent" />
            </label>
            {ui.hl.length > 0 && (
              <button type="button" onClick={() => patch({ hl: [] })}
                className="rounded-full border border-accent/30 bg-accent-soft px-3 py-1 text-[12.5px] font-semibold text-accent">
                Agent highlighted {ui.hl.length} {ui.hl.length === 1 ? "trend" : "trends"} · show all ×</button>
            )}
            {(focus || ui.f.type || ui.f.brand || ui.f.life || ui.f.q) && (
              <button type="button" className="text-[12.5px] font-semibold text-accent"
                onClick={() => { setFocus(""); patch({ f: { type: "", brand: "", life: "", q: "" } }); }}>
                Clear{focus ? ` · ${FOCUS_LABEL[focus]}` : ""} ×</button>
            )}
          </div>
        )}
        {hint && <p role="status" className="mt-3 rounded-md bg-warn-soft px-3 py-1.5 text-[13px] text-warn">{hint}</p>}

        </div>

        <main ref={scroller} className="mt-3 min-h-0 flex-1 overflow-y-auto pb-20 [scrollbar-width:thin]">
          <AnimatePresence mode="wait">
            <motion.div key={view === "detail" ? `detail-${ui.sel}` : view} initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.22 }}>
              {view === "map" && (
                <div className="rounded-xl border border-line bg-card p-2 pb-3 shadow-[var(--shadow)]">
                  <OpportunityMap trends={state.trends} matches={matches} selected={ui.sel} board={ui.board} highlight={ui.hl} onOpen={open} />
                  <p className="px-2 pt-1 text-[11.5px] text-ink3">{matches.size} of {state.trends.length} trends shown. Click a bubble to open it.</p>
                </div>
              )}
              {view === "list" && (
                <ListView state={state} trends={state.trends} matches={matches} board={ui.board} cmp={ui.cmp}
                  brand={ui.f.brand} onOpen={open} onBoard={toggleBoard} onCmp={toggleCmp} />
              )}
              {view === "detail" && trend && (
                <Detail state={state} trend={trend} metric={ui.metric} onMetric={(m: Metric) => patch({ metric: m })}
                  board={ui.board} onBoard={toggleBoard} onBack={() => goto(home)} onAsk={ask} onCmp={startCompare} origin={origin} />
              )}
              {view === "heatmap" && <Heatmap state={state} matches={matches} highlight={ui.hl} onOpen={open} />}
              {view === "timeline" && <Timeline state={state} matches={matches} highlight={ui.hl} onOpen={open} />}
              {view === "compare" && <Compare state={state} ids={ui.cmp} onOpen={open} onRemove={toggleCmp} onAsk={ask} />}
              {view === "board" && <Board state={state} ids={ui.board} onOpen={open} onRemove={toggleBoard} onAsk={ask} />}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </TipProvider>
  );
}

function chipsFor(view: ViewId, trend: Trend | null, ui: Ui, state: TrendsState): string[] {
  if (view === "detail" && trend) {
    return [`Is ${trend.name} worth a bigger buy?`, "Which trend is most similar to this?"];
  }
  if (view === "compare") return ["Which one should I buy into first?", "Show my whitespace gaps"];
  if (view === "board") return ["Which board trends should I buy into first?"];
  const brand = state.brands.find((b) => b.id === ui.f.brand);
  return ["Where are my biggest whitespace gaps?", "Which trends are fading but heavily stocked?",
    brand ? `What should ${brand.name} buy into this season?` : "Which trends are accelerating fastest?"];
}

/** True from the moment an action is posted until the agent's reply remounts the page. */
function useBusy(): boolean {
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let timer: number | undefined;
    const off = onAction(() => {
      setBusy(true);
      window.clearTimeout(timer);
      timer = window.setTimeout(() => setBusy(false), BUSY_TIMEOUT_MS);
    });
    return () => {
      off();
      window.clearTimeout(timer);
    };
  }, []);
  return busy;
}
