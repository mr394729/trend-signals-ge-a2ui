---
name: ge-agentic-workspace
description: Builds an agent-driven workspace for Gemini Enterprise - a custom HTML page in the Canvas side panel (A2UI v0.9 IFrameSrcdoc) that shares state with an ADK agent in the chat - using this repository as the reference implementation. Use when asked for a rich analytics or "enterprise SaaS" UI inside Gemini Enterprise, a dashboard or workspace in the Canvas, an HTML iframe experience that talks to an agent, when adapting Trend Signals to new data, tools or views, when an iframe will not scroll or fill the panel, or when Gemini Enterprise reports "connection to the server was lost". Covers the app-shell layout, the two-way state loop, tool design, time limits, styling and testing.
metadata:
  version: "1.0"
  a2ui: "v0.9"
allowed-tools: Bash Read Write Edit
---

# Gemini Enterprise agentic workspace

The reference implementation is this repository. Read `docs/HOW_IT_WORKS.md` first, then `src/trend_signals/` and
`frontend/src/`. The generic version of these rules, independent of this codebase, is
`skills/gemini-enterprise-a2ui/references/agentic_workspace.md`; use the `gemini-enterprise-a2ui` skill for A2UI
components, messages and validation.

## The design

- Page: React and Vite built to one HTML file, delivered in `Canvas > IFrameSrcdoc`. The frame is sealed (no network,
  no navigation), so all data and state are injected into the HTML.
- Page to agent: the only channel is `postMessage {type:'a2ui_action', action, data:{...viewState, prompt}}`.
  `data.prompt` becomes the user's message and `data` is the action context. Send the whole view state with every action.
- Agent to page: tools write a shared `ui_state`; after the final reply the server renders the page again and attaches
  the new Canvas surface to the closing message. An open Canvas cannot be updated, so every reply is a new surface.
- Local interactions (tabs, filters, drill-down, hover, zoom, board) are client state and never leave the page.

## Rules

1. **App shell, fixed frame.** `IFrameSrcdoc.height` is pixels only and the Canvas panel does not scroll. Use one fixed
   height (1024 works) and a page of `h-dvh flex-col` with a pinned header and a `min-h-0 flex-1 overflow-y-auto pb-20`
   content region. Never a long page; never size the frame from the screen height.
2. **Read the structured action context**, not the flattened `Selected:` text line (it loses `;` and `=`). State is per
   conversation (the A2A `contextId`), never keyed by caller-set metadata; it is in memory here, so the service runs one instance. Use a shared store before scaling out.
3. **Put the open view in the user message** (`[Workspace right now: ...]`). The system instruction alone loses to
   earlier turns.
4. **Write the reply text after the tool calls**, and attach the surface to the closing message: text in a `working`
   update is shown under "Show thinking".
5. **Time limits.** Model call timeout about 40 s with retries, turn budget about 85 s with a plain message when it
   expires. Gemini Enterprise gives up on a slow agent with "connection to the server was lost".
6. **Open the workspace deterministically** (greeting or an "open ..." phrase), without a model call.
7. **Tailwind utilities live in a CSS layer**; unlayered CSS overrides them. Keep all other CSS in layers.
8. **Tool signatures.** Test `FunctionTool(fn)._get_declaration()` for every tool; take structured items as delimited
   strings and reject bad ones with an actionable message.
9. **Validate** every surface against the composite catalog and keep one A2UI message under 1 MiB.
10. **API testing.** The Gemini Enterprise per-agent endpoint takes text parts only: simulate a click as one
    `Selected: action; k=v` text part and nothing else (`scripts/ge_client.py --action-as text`).
11. **Theme.** Gemini Enterprise does not pass its theme to the frame; ship a light and dark toggle and use tokens, not
    fixed colors.
12. **No images in the frame.** Draw illustrations and textures as SVG.

## Styling (Tailwind v4, Radix, tokens)

Full detail: `docs/THEMING.md`. In short:
- Colors live only in custom properties in `frontend/src/lib/tokens.css`; `[data-theme="dark"]` redefines the same names.
- `@theme inline { --color-card: var(--surface); ... }` gives Tailwind role names (`bg-card`, `text-ink3`,
  `border-line`, `bg-accent-soft`); `inline` lets the theme switch re-theme every utility without a rebuild. Never use
  `text-white` on the accent color: use `text-[var(--on-accent)]`.
- Radix for behavior, Tailwind for looks, states via `data-[state=active]:` and similar variants.
- Data colors (lifecycle, series, heatmap `color-mix`) come inline from the data; SVG uses theme classes.

## Recipe: a new workspace from this one

1. Keep `src/trend_signals/kit/` (the A2UI and Gemini Enterprise plumbing); replace `catalog.py`, `tools.py`,
   `prompts.py`, `state.py` and the views in `frontend/src/scenes/`.
2. Define the state dict and its TypeScript type together; include `ui` (view, selection, filters, highlights, scroll).
3. Build the shell and views; keep a dev fixture (`make fixture`, `make gallery`) so the page can be designed without the agent.
4. Tools: read tools return compact data; write tools set `ui_state` and call `request_update`; one tool chooses the view.
5. Executor: deterministic open path, click handling, state in the click message, canvas render after the reply, time limits.
6. Tests (`make test`): state, click parsing, tool declarations, catalog validation, part order of the open reply,
   turn timeout. Render every view (`make screenshots`).
7. Deploy (`make deploy`: private Cloud Run, stable URL pinned, invoker role for the Discovery Engine service agent),
   then `make register`. Re-run `make register` after any change to the agent card.
8. Verify through the API (`scripts/ge_client.py`) and, for rendering and clicks, in the Gemini Enterprise web app.
