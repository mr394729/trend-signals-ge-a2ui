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

// DEV-ONLY: loads the fixture exported from the Python dataset (`make fixture`), so
// `npm run dev` renders the workspace with no agent. Imported behind import.meta.env.DEV.

import fixture from "./fixture.json";
import type { TrendsState } from "@/lib/trends";

export function loadDevState(): TrendsState {
  const params = new URLSearchParams(window.location.search);
  const state = structuredClone(fixture) as unknown as TrendsState;
  const view = params.get("view");
  if (view === "map" || view === "list" || view === "detail" || view === "compare" || view === "board") {
    state.ui.view = view;
  }
  const sel = params.get("sel");
  if (sel) state.ui.sel = sel;
  if (params.get("board")) state.ui.board = (params.get("board") as string).split(",");
  if (params.get("cmp")) state.ui.cmp = (params.get("cmp") as string).split(",");
  return state;
}
