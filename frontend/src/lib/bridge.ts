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

// The only channel from the sealed iframe to the agent: a postMessage to Gemini Enterprise.
//
// Gemini Enterprise handles `{ type: "a2ui_action", action, data }` from an IFrameSrcdoc. It turns
// `data` into the action context and shows `data.prompt` as the user's message in the chat; the
// agent then receives an ordinary turn (the prompt, plus the context). The frame cannot call the
// agent and cannot receive a reply: a reply is a new Canvas surface, which remounts this page with
// fresh state.

export type ActionValue = string | number | boolean | null;

export interface SendActionArgs {
  action: string;
  /** Becomes the user's message in the chat. */
  prompt: string;
  /** The canvas state and anything else the agent should know. */
  data?: Record<string, ActionValue>;
}

type Listener = (args: SendActionArgs) => void;
const listeners = new Set<Listener>();

/** In-frame observers of outgoing actions (the "agent is working" indicator). */
export function onAction(fn: Listener): () => void {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}

export function sendAction(args: SendActionArgs): void {
  listeners.forEach((fn) => fn(args));
  if (window.parent === window) {
    // eslint-disable-next-line no-console
    console.debug("[bridge] standalone (no Gemini Enterprise host); action not delivered", args);
    return;
  }
  // targetOrigin "*": the srcdoc sandbox has an opaque origin and the host's is not known to it.
  window.parent.postMessage(
    { type: "a2ui_action", action: args.action, data: { ...(args.data ?? {}), prompt: args.prompt } },
    "*",
  );
}
