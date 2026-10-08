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

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { readState } from "@/lib/trends";
import { TrendsScene } from "@/scenes/TrendsScene";
import "./styles.css";

async function boot(): Promise<void> {
  const root = document.getElementById("root");
  if (!root) return;
  let state = readState();

  // `npm run dev` without an injected state: load the illustrative fixture so the page can be
  // designed without the agent. Dead-code-eliminated from the production bundle.
  if (!state && import.meta.env.DEV) {
    const { loadDevState } = await import("./dev/devBoot");
    state = loadDevState();
  }

  if (!state) {
    root.textContent = "No workspace state was provided. Ask the agent to open the trend workspace.";
    root.className = "no-state";
    return;
  }
  createRoot(root).render(
    <StrictMode>
      <TrendsScene state={state} />
    </StrictMode>,
  );
}

void boot();
