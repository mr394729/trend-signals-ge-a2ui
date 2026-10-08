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

// Small component kit in the shadcn/ui style: Radix primitives (behaviour, keyboard, ARIA) styled
// with Tailwind utilities over the theme tokens.

import * as Select from "@radix-ui/react-select";
import * as Tabs from "@radix-ui/react-tabs";
import * as ToggleGroup from "@radix-ui/react-toggle-group";
import * as Tooltip from "@radix-ui/react-tooltip";
import { Check, ChevronDown } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { LIFE_COLOR, LIFE_LABEL, type Life } from "@/lib/trends";
import { cn } from "@/lib/cn";

export interface Option { value: string; label: string }

export function ViewTabs({ value, onChange, items }: {
  value: string; onChange: (v: string) => void; items: { value: string; label: ReactNode }[];
}) {
  return (
    <Tabs.Root value={value} onValueChange={onChange}>
      <Tabs.List aria-label="Views" className="flex gap-6 border-b border-line overflow-x-auto">
        {items.map((i) => (
          <Tabs.Trigger key={i.value} value={i.value}
            className={cn("relative -mb-px whitespace-nowrap pb-2.5 pt-1 font-serif text-[14.5px] font-semibold text-ink3",
              "transition-colors hover:text-ink data-[state=active]:text-ink",
              "after:absolute after:inset-x-0 after:-bottom-px after:h-[2px] after:bg-transparent",
              "data-[state=active]:after:bg-accent")}>
            {i.label}
          </Tabs.Trigger>
        ))}
      </Tabs.List>
    </Tabs.Root>
  );
}

export function Segmented({ value, onChange, options, label }: {
  value: string; onChange: (v: string) => void; options: Option[]; label: string;
}) {
  return (
    <ToggleGroup.Root type="single" value={value} aria-label={label}
      onValueChange={(v) => onChange(v || value)}
      className="inline-flex rounded-full border border-line bg-card p-0.5">
      {options.map((o) => (
        <ToggleGroup.Item key={o.value} value={o.value}
          className={cn("rounded-full px-3.5 py-1 text-[13px] font-medium text-ink3 transition-colors hover:text-ink",
            "data-[state=on]:bg-accent data-[state=on]:text-[var(--on-accent)]")}>
          {o.label}
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  );
}

const ALL = "__all";

export function Pick({ value, onChange, options, allLabel, label }: {
  value: string; onChange: (v: string) => void; options: Option[]; allLabel: string; label: string;
}) {
  return (
    <Select.Root value={value || ALL} onValueChange={(v) => onChange(v === ALL ? "" : v)}>
      <Select.Trigger aria-label={label}
        className={cn("inline-flex items-center gap-2 rounded-full border border-line bg-card px-3.5 py-1.5 text-[13px]",
          "text-ink2 hover:border-ink4 data-[placeholder]:text-ink3")}>
        <Select.Value />
        <Select.Icon><ChevronDown size={14} /></Select.Icon>
      </Select.Trigger>
      <Select.Portal>
        <Select.Content position="popper" sideOffset={6}
          className="z-50 min-w-[160px] overflow-hidden rounded-xl border border-line bg-card p-1 shadow-lg">
          <Select.Viewport>
            {[{ value: ALL, label: allLabel }, ...options].map((o) => (
              <Select.Item key={o.value} value={o.value}
                className="flex cursor-pointer items-center justify-between gap-6 rounded-lg px-2.5 py-1.5 text-[13px] text-ink2 outline-none data-[highlighted]:bg-accent-soft data-[highlighted]:text-ink">
                <Select.ItemText>{o.label}</Select.ItemText>
                <Select.ItemIndicator><Check size={13} /></Select.ItemIndicator>
              </Select.Item>
            ))}
          </Select.Viewport>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
  );
}

export function Tip({ content, children }: { content: ReactNode; children: ReactNode }) {
  return (
    <Tooltip.Root delayDuration={0}>
      <Tooltip.Trigger asChild>{children}</Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content sideOffset={10}
          className="z-50 rounded-lg bg-[var(--tip-bg)] px-3 py-2 text-[12px] leading-snug text-[var(--tip-fg)] shadow-lg">
          {content}
          <Tooltip.Arrow className="fill-[var(--tip-bg)]" />
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}

export const TipProvider = Tooltip.Provider;

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <section className={cn("rounded-xl border border-line bg-card p-5 shadow-[var(--shadow)]", className)}>{children}</section>;
}

export function CardTitle({ children, aside }: { children: ReactNode; aside?: ReactNode }) {
  return (
    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
      <h3 className="font-serif text-[17px] font-medium text-ink">{children}</h3>{aside}
    </div>
  );
}

export function Btn({ variant = "default", on, className, ...rest }: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "default" | "primary"; on?: boolean;
}) {
  return (
    <button {...rest} className={cn(
      "inline-flex items-center gap-1.5 rounded-full border px-4 py-2 text-[13px] font-medium transition-colors disabled:opacity-50",
      variant === "primary" ? "border-accent bg-accent text-[var(--on-accent)] hover:opacity-90"
        : on ? "border-accent/40 bg-accent-soft text-accent" : "border-line bg-card text-ink2 hover:border-ink4",
      className)} />
  );
}

export function Tag({ children, tone = "accent" }: { children: ReactNode; tone?: "accent" | "neutral" }) {
  return (
    <span className={cn("inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-[10.5px] font-bold uppercase tracking-[.08em]",
      tone === "accent" ? "bg-accent-soft text-accent" : "bg-line2 text-ink3")}>{children}</span>
  );
}

export function LifePill({ life }: { life: Life }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[12px] font-semibold" style={{ color: LIFE_COLOR[life] }}>
      <i className="inline-block size-2 rounded-full" style={{ background: LIFE_COLOR[life] }} />{LIFE_LABEL[life]}
    </span>
  );
}

export function Momentum({ v }: { v: number }) {
  const tone = v >= 4 ? "text-good" : v <= -4 ? "text-bad" : "text-ink3";
  return <span className={cn("text-[12.5px] font-bold tabular-nums", tone)}>{v >= 4 ? "▲" : v <= -4 ? "▼" : "•"} {v > 0 ? "+" : ""}{v}</span>;
}

export function Bar({ value, tone = "accent", className }: { value: number; tone?: "accent" | "warn" | "good"; className?: string }) {
  const bg = tone === "warn" ? "bg-warn" : tone === "good" ? "bg-good" : "bg-accent";
  return (
    <span className={cn("block h-1.5 min-w-10 flex-1 overflow-hidden rounded-full bg-line2", className)}>
      <i className={cn("block h-full rounded-full", bg)} style={{ width: `${Math.max(2, Math.min(100, value))}%` }} />
    </span>
  );
}
