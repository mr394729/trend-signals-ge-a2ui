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

// Contract for the Trend Signals srcdoc scene. MUST stay in lock-step with
// `agents/trends/app/state.py` (+ catalog.py) — the server injects this as
// `window.__TREND_SIGNALS_STATE__`; the iframe can never fetch (CSP connect-src 'none').

export type TrendType = "style" | "aesthetic" | "fabric" | "color";
export type Life = "emerging" | "growth" | "peak" | "mature" | "decline";
export type ViewId = "map" | "list" | "heatmap" | "timeline" | "detail" | "compare" | "board";
export type Metric = "overall" | "tiktok" | "pinterest" | "search" | "editorial" | "runway";

export interface Channel { id: Metric; label: string; value: number; delta: number }
export interface Swatch { hex: string; name: string }
export interface Dna { palette: Swatch[]; silhouettes: string[]; fabrics: string[]; moods: string[]; shape: string }
export interface Trend {
  id: string; name: string; type: TrendType; life: Life;
  strength: number; momentum: number; coverage: number; volume: number;
  fit: Record<string, number>;
  series: Record<Metric, number[]>;
  band: [number, number][];
  peak_week: string; lifecycle_pos: number;
  channels: Channel[]; drivers: string[]; dna: Dna;
  products: { sku: string; match: number }[];
  articles: { title: string; source: string; date: string }[];
  quick_read: string;
}
export interface Product {
  id: string; name: string; brand: string; dept: string; shape: string; hex: string;
  price: number; sell_through: number; weeks_cover: number;
}
export interface Rec { priority: "high" | "medium" | "low"; owner: string; timing: string; action: string; why: string }
export interface Filters { type: string; brand: string; life: string; q: string }
export interface Ui {
  /** hl: trends the agent pointed out; sy: scroll offset restored after a re-render. */
  view: ViewId; sel: string; cmp: string[]; board: string[]; metric: Metric; hl: string[]; sy: number;
  f: Filters;
}
export interface TrendsState {
  scene: "trends";
  retailer: string;
  brands: { id: string; name: string }[];
  types: Record<TrendType, string>;
  lifecycles: Life[];
  weeks: string[]; hist: number; fc: number; as_of: string;
  trends: Trend[];
  products: Record<string, Product>;
  kpis: { tracked: number; rising: number; whitespace: number; at_risk: number };
  ui: Ui;
  recs: Record<string, Rec[]>;
  note: string;
  suggestions: string[];
}

export const LIFE_LABEL: Record<Life, string> = {
  emerging: "Emerging", growth: "Growth", peak: "Peak", mature: "Mature", decline: "Decline",
};
// Lifecycle identity colors (categorical, never the sentiment trio).
export const LIFE_COLOR: Record<Life, string> = {
  emerging: "#12b5cb", growth: "#1e8e3e", peak: "#1a73e8", mature: "#f9ab00", decline: "#9aa0a6",
};
export const METRIC_LABEL: Record<Metric, string> = {
  overall: "Overall", tiktok: "TikTok", pinterest: "Pinterest", search: "Search",
  editorial: "Editorial", runway: "Runway",
};

export const isWhitespace = (t: Trend) => t.strength >= 60 && t.coverage < 45;
export const isAtRisk = (t: Trend) => (t.life === "mature" || t.life === "decline") && t.coverage >= 65;
export const opportunity = (t: Trend) => Math.round((t.strength * (100 - t.coverage)) / 100);

export function weekLabel(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/** Canvas state as click params — what the agent learns with every action. */
export function uiParams(ui: Ui, scrollTop = 0): Record<string, string> {
  const j = (a: string[]) => (a.length ? a.join(",") : "-");
  return {
    view: ui.view, sel: ui.sel || "-", cmp: j(ui.cmp), board: j(ui.board), metric: ui.metric, hl: j(ui.hl),
    sy: String(Math.max(0, Math.round(scrollTop))),
    ft: ui.f.type || "-", fb: ui.f.brand || "-", fl: ui.f.life || "-", fq: ui.f.q || "-",
  };
}

declare global {
  interface Window {
    __TREND_SIGNALS_STATE__?: TrendsState;
  }
}

/** The state the server injected, or null (a loose gate: enough to route safely). */
export function readState(): TrendsState | null {
  const s = typeof window === "undefined" ? undefined : window.__TREND_SIGNALS_STATE__;
  return s && typeof s === "object" && s.scene === "trends" ? s : null;
}
