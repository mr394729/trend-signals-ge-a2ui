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

import * as Dialog from "@radix-ui/react-dialog";
import { Command } from "cmdk";
import { CornerDownLeft, LayoutGrid, List, Scale, Search, Sparkles, Star } from "lucide-react";
import { useState, type ReactNode } from "react";
import { LifePill } from "@/components";
import type { Trend, ViewId } from "@/lib/trends";

const ITEM = "flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-[14px] text-ink2 aria-selected:bg-accent-soft aria-selected:text-ink";

export function Palette({ open, onOpenChange, trends, onOpenTrend, onGoto, onAsk, questions }: {
  open: boolean; onOpenChange: (o: boolean) => void; trends: Trend[]; onOpenTrend: (id: string) => void;
  onGoto: (v: ViewId) => void; onAsk: (q: string) => void; questions: string[];
}) {
  const [text, setText] = useState("");
  const q = text.trim().toLowerCase();
  const hit = (v: string) => !q || v.toLowerCase().includes(q);
  const done = (fn: () => void) => () => { onOpenChange(false); setText(""); fn(); };
  const views: [ViewId, string, ReactNode][] = [
    ["map", "Opportunity map", <LayoutGrid key="m" size={15} />], ["list", "Ranked list", <List key="l" size={15} />],
    ["compare", "Compare", <Scale key="c" size={15} />], ["board", "Board", <Star key="b" size={15} />]];
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/35 backdrop-blur-[2px]" />
        <Dialog.Content aria-label="Command palette"
          className="fixed left-1/2 top-[8vh] z-50 w-[min(560px,92vw)] -translate-x-1/2 overflow-hidden rounded-2xl border border-line bg-card shadow-2xl">
          <Dialog.Title className="sr-only">Search or ask</Dialog.Title>
          <Command label="Search trends or ask the agent" loop shouldFilter={false}>
            <div className="flex items-center gap-2 border-b border-line px-4">
              <Search size={16} className="text-ink4" />
              <Command.Input value={text} onValueChange={setText} placeholder="Search trends, jump to a view, or ask the agent…"
                className="h-12 flex-1 bg-transparent text-[15px] text-ink outline-none focus-visible:outline-none placeholder:text-ink4" />
              <kbd className="rounded border border-line px-1.5 text-[11px] text-ink3">esc</kbd>
            </div>
            <Command.List className="max-h-[52vh] overflow-y-auto p-2">
              <Command.Empty className="px-3 py-6 text-center text-[13px] text-ink3">No match. Press enter to ask the agent.</Command.Empty>
              {text.trim() && (
                <Command.Group heading="Ask the agent" className="mb-1 text-[10.5px] font-bold uppercase tracking-wider text-ink3 [&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1">
                  <Command.Item value={`ask ${text}`} onSelect={done(() => onAsk(text.trim()))} className={ITEM}>
                    <Sparkles size={15} className="text-accent" /><span className="flex-1 truncate normal-case tracking-normal font-normal">{text.trim()}</span>
                    <CornerDownLeft size={14} className="text-ink4" /></Command.Item>
                </Command.Group>
              )}
              {views.some(([, l]) => hit(l)) && <Command.Group heading="Go to" className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1 [&_[cmdk-group-heading]]:text-[10.5px] [&_[cmdk-group-heading]]:font-bold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:text-ink3">
                {views.filter(([, label]) => hit(label)).map(([v, label, icon]) => (
                  <Command.Item key={v} value={`go ${label}`} onSelect={done(() => onGoto(v))} className={ITEM}>{icon}{label}</Command.Item>))}
              </Command.Group>}
              {trends.some((t) => hit(`${t.name} ${t.type} ${t.life}`)) && <Command.Group heading="Trends" className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1 [&_[cmdk-group-heading]]:text-[10.5px] [&_[cmdk-group-heading]]:font-bold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:text-ink3">
                {trends.filter((t) => hit(`${t.name} ${t.type} ${t.life}`)).map((t) => (
                  <Command.Item key={t.id} value={`trend ${t.name} ${t.type} ${t.life}`} onSelect={done(() => onOpenTrend(t.id))} className={ITEM}>
                    <span className="flex-1 truncate font-serif text-[16px]">{t.name}</span><LifePill life={t.life} />
                    <span className="w-8 text-right font-serif tabular-nums">{t.strength}</span></Command.Item>))}
              </Command.Group>}
              {questions.some(hit) && <Command.Group heading="Suggested questions" className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1 [&_[cmdk-group-heading]]:text-[10.5px] [&_[cmdk-group-heading]]:font-bold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:text-ink3">
                {questions.filter(hit).map((qq) => (
                  <Command.Item key={qq} value={`question ${qq}`} onSelect={done(() => onAsk(qq))} className={ITEM}>
                    <Sparkles size={15} className="text-accent" />{qq}</Command.Item>))}
              </Command.Group>}
            </Command.List>
          </Command>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
