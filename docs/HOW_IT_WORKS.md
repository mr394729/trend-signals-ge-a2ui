# How it works

This document explains how the Trend Signals workspace is built, in the order a request travels through it. It
covers the page, the agent, the state that connects them, the Gemini Enterprise behaviors the design depends on, and
the reasoning behind each choice. [ARCHITECTURE.md](ARCHITECTURE.md) is the short reference; this is the long form.

Contents

1. [The shape of the system](#1-the-shape-of-the-system)
2. [The three layers of the code](#2-the-three-layers-of-the-code)
3. [A request, step by step](#3-a-request-step-by-step)
4. [The page: an app shell in a fixed frame](#4-the-page-an-app-shell-in-a-fixed-frame)
5. [The state contract](#5-the-state-contract)
6. [The agent](#6-the-agent)
7. [Visualization techniques](#7-visualization-techniques)
8. [Theming](#8-theming)
9. [Time limits](#9-time-limits)
10. [Testing](#10-testing)
11. [Deployment and registration](#11-deployment-and-registration)
12. [Gemini Enterprise behaviors the design depends on](#12-gemini-enterprise-behaviors-the-design-depends-on)
13. [Adapting it](#13-adapting-it)

## 1. The shape of the system

The product is two things that share one state: a workspace in the Canvas side panel and an agent in the chat.

```
        Gemini Enterprise
   ┌───────────────┬──────────────────────────┐
   │ Chat          │ Canvas side panel        │
   │  user text    │  IFrameSrcdoc            │
   │  agent reply  │   React page (one file)  │
   │  chips        │   views, charts, filters │
   └──────┬────────┴─────────────┬────────────┘
          │ A2A message          │ postMessage a2ui_action {state, prompt}
          ▼                      ▼
   ┌─────────────────────────────────────────┐
   │ Agent service (Cloud Run)               │
   │  executor ── ADK agent ── tools ──┐     │
   │      │                            ▼     │
   │      └──── renders Canvas ◄── ui_state  │
   └─────────────────────────────────────────┘
```

Two properties define the design:

* **The page is sealed.** It cannot call the agent or the network. Everything it shows is in the state injected with
  the page, and the only thing it can send out is an action message to Gemini Enterprise.
* **A reply is a new page.** The agent cannot update an open Canvas. It sends a new Canvas surface, which reopens the
  panel with the state the agent chose. Continuity is the responsibility of the state, not of the DOM.

The rest of the document follows from these two.

## 2. The three layers of the code

| Layer | Path | Knows about | Reusable? |
|---|---|---|---|
| Protocol kit | `src/trend_signals/kit/` | A2UI v0.9, the Gemini Enterprise catalog, A2A parts, clicks, identity, page injection | Yes: copy it into any agent |
| Use case | `src/trend_signals/` (`catalog`, `state`, `ui_state`, `tools`, `prompts`, `agent`, `canvas`, `executor`, `card`, `main`) | Trends, brands, SKUs, the workspace | No: this is what you replace |
| Page | `frontend/` | The state shape, the views | The shell and components, yes; the views are the use case |

The kit contains no trend logic. `kit/v09.py` builds surfaces and validates every one against the Gemini Enterprise
composite catalog with the public A2UI Agent SDK (`kit/sdk.py`), so an invalid surface raises in the service and in
the tests. `kit/actions.py` and `kit/click_bridge.py` normalize every shape in which a click can arrive.
`kit/final_panel.py` attaches a rendered surface to the event Gemini Enterprise shows as the answer.
`kit/srcdoc.py` splices state into the page.

## 3. A request, step by step

There are three kinds of turn. All three end in one reply: a text part, zero or more A2UI parts, and a suggestions
part.

### 3.1 Opening the workspace (deterministic)

`executor.route` sends a greeting, `open`, or a phrase such as "Open the trend workspace" (`_OPEN_RE`) down the open
path. No model is called:

1. `canvas.render(user)` calls `state.build(user, chips)`, which assembles the dataset, the user's `ui` state, the
   recommendations written so far, a one-shot note and the suggestion chips.
2. `kit/srcdoc.render` reads the built bundle (`frontend/dist/index.html`) and inserts
   `<script>window.__TREND_SIGNALS_STATE__={...};</script>` before `</head>`, escaping every `<` as `\u003c`.
3. `kit/v09.Surface` builds `Canvas > IFrameSrcdoc(htmlContent, height=1024)` and validates it.
4. `response_parts` orders the reply: text, A2UI messages, suggestions.

The open turn takes about two seconds, and most of that is Gemini Enterprise.

### 3.2 A typed question (agent)

The text goes to the ADK agent. The instruction is built on every model call (`agent._instruction_provider`) and ends
with what the canvas showed at the user's last action (`ui_state.describe`). The model calls tools and writes one reply
after the last tool call. A tool that changes what the user sees sets state and calls `ui_state.request_update`. When
the final response event arrives, `executor._CanvasInjector` checks `ui_state.take_update`; if a tool asked for an
update it renders the canvas and stashes it. `final_panel.FinalPanelQueue` attaches the stash to the closing
artifact, which is where Gemini Enterprise shows it (a surface attached to an earlier `working` update ends up under
"Show thinking").

### 3.3 A canvas action (agent, with state)

A click in the page calls `sendAction` (`frontend/src/lib/bridge.ts`):

```ts
window.parent.postMessage({ type: "a2ui_action", action: "ask",
  data: { ...workspaceState, prompt: "Recommend actions for Barrel-leg denim" } }, "*");
```

Gemini Enterprise shows `data.prompt` as the user's message and sends the agent a message with a text part and a v0.9
action data part whose `context` is `data`. The executor then:

1. `read_click` reads the structured context. It prefers the structured action over the flattened
   `Selected: ask; k=v` line, because the line cannot carry values that contain `;` or `=`.
2. `ui_state.remember_click` stores the workspace state: view, selected trend, comparison, board, highlights, metric,
   filters, scroll offset.
3. `_request_converter` replaces the model's input with the prompt followed by
   `[Workspace right now: view=detail; selected trend: Chocolate brown; board: Butter yellow]`.
4. The agent runs as in 3.2.

Step 3 exists because of an observed failure. With the state only in the system instruction, a conversation that had
discussed one trend made the model answer about it even when the user had another open and asked about "this trend".
Putting the state in the user message resolved it.

## 4. The page: an app shell in a fixed frame

### 4.1 Why a shell

The Canvas panel does not scroll its content, and the frame has no "fill the panel" option: `IFrameSrcdoc.height` is a
fixed number of pixels. A long page in a frame therefore either leaves white space below it (frame too short for the
panel) or hides its own bottom (frame taller than the panel, with nothing to scroll). Sizing the frame from the user's
screen height was tried and abandoned: the page cannot see the panel, and the first render has no information.

The page is built as an application shell instead (`TrendsScene.tsx`):

```
<div class="flex h-dvh flex-col">          ← exactly the frame height
  <div class="shrink-0"> header, stats, tabs, filters </div>   ← stays put
  <main class="min-h-0 flex-1 overflow-y-auto pb-20"> view </main>   ← scrolls
</div>
```

The frame is a fixed 1024 px (`canvas.FRAME_HEIGHT`). The page always fills it, scrolling happens inside it, and the
bottom padding means a frame that is slightly taller than the panel hides only padding.

### 4.2 The build

* **Vite single file.** `vite-plugin-singlefile` inlines all JavaScript and CSS into one `index.html` (about 560 KB).
  The frame cannot load anything from a URL.
* **CSP meta.** `vite.config.ts::geSrcdocCsp` adds `connect-src 'none'` at build time. It keeps the file offline when
  opened directly; Gemini Enterprise removes the element and applies its own policy.
* **State injection.** The server splices the state at emission time. A dev build with no injected state loads
  `src/dev/fixture.json` (exported from the Python dataset by `make fixture`), so the page can be designed without the
  agent.

### 4.3 The stack

| Concern | Choice | Reason |
|---|---|---|
| Styling | Tailwind CSS v4 over CSS custom properties (`lib/tokens.css`) | Utilities with theme tokens; the light and dark themes are a token swap |
| Behavior | Radix primitives (tabs, toggle group, select, tooltip, dialog) in a shadcn-style kit (`components.tsx`) | Keyboard handling and ARIA that would otherwise be rebuilt |
| Charts | d3 scales, shapes and arrays, rendered as React SVG | Full control of annotation and interaction; exact data positions |
| Motion | Motion (`motion/react`) | Entrance springs, path drawing, a circular reveal, page cross-fades |
| Icons | Lucide | Consistent line icons |
| Command palette | cmdk in a Radix dialog (`palette.tsx`) | Search, jump and ask in one place |

Tailwind's utilities load into a CSS layer (`@import "tailwindcss"`); any unlayered CSS would beat them, which is why
the page has none apart from two small base rules inside `@layer base`.

### 4.4 Interactions that stay local

Tab switches, filters, drill-down, the board, the comparison, chart hover, brush zoom and the palette are React state.
They never leave the page. Only an action that needs the agent calls `sendAction`, and the page shows an "Agent is
working…" pill from that moment until the reply replaces the page.

## 5. The state contract

The state is one dict built by `state.build` and typed in `frontend/src/lib/trends.ts` (`TrendsState`). Keep the two in
step.

| Part | Content |
|---|---|
| Dataset | trends (series, forecast band, channels, drivers, visual DNA, matches, articles), products, brands, KPIs |
| `ui` | `view`, `sel`, `cmp`, `board`, `hl` (highlights), `metric`, `f` (filters), `sy` (scroll offset) |
| `recs` | recommended actions the agent wrote, by trend |
| `note` | a one-shot banner ("Highlighted the five biggest whitespace gaps") |
| `suggestions` | follow-up chips |

`ui_state.py` holds `ui` per conversation (keyed by the A2A `contextId`), in memory. Two directions write to it:

* **Canvas to agent.** `uiParams(ui, scrollTop)` flattens `ui` into string params sent with every action;
  `remember_click` parses them back (an unknown view or metric is ignored).
* **Agent to canvas.** The tools `show_in_canvas`, `update_board` and `save_recommendations` change it. After the
  reply the canvas is rendered from it.

Scroll continuity: the page sends the scroll offset of its content region (`sy`); the agent resets it to 0 when it
navigates to a different view or trend (`tools._navigate`) and leaves it alone otherwise, and the page restores it on
mount.

The in-memory store is the reason the service runs with `--max-instances 1`. Two instances would each hold a different
`ui` for one conversation.

## 6. The agent

### 6.1 Tools

| Tool | Reads or writes | Purpose |
|---|---|---|
| `search_trends`, `get_trend`, `compare_trends`, `scan_assortment` | reads | Compact, grounded data for the model (rows, forecast, channels, matched SKUs, whitespace and risk lists) |
| `show_in_canvas` | writes | Choose the view, trend, comparison, filters and highlighted trends, and a banner note |
| `update_board` | writes | Edit the shortlist |
| `save_recommendations` | writes | Store two to four actions for a trend; shown in the detail view |

`save_recommendations` takes `"priority | owner | timing | action | why"` strings and rejects malformed ones with a message
the model can act on. This avoids an open-ended object schema in the function declaration. The tests build the
declaration of every tool, so an unsupported signature fails in CI and not on the first live turn.

### 6.2 The instruction

`prompts.build_instruction` states the retailer, the metrics, the canvas and its views, how to use each tool, when to
highlight, and the reply format: call every tool first, then write one reply after the last tool call (text before or
between calls is lost), lead with the answer and numbers, mention what changed on the canvas, end with one next step,
and never expose internal ids.

### 6.3 ADK specifics that matter in Gemini Enterprise

* The reply text must come after the tool calls; Gemini Enterprise shows only the final message.
* The final response event is converted by `_CanvasInjector`; the surface is stashed there and attached to the
  closing artifact by `final_panel`, and the dedup in `final_panel` keeps ADK's closing artifact from repeating it.
* `A2aAgentExecutor` is created with `use_legacy=True` and a custom event and request converter.

## 7. Visualization techniques

All charts are SVG drawn by React with d3 scales. None uses a charting component library.

* **Opportunity map** (`Charts.tsx::OpportunityMap`). X is trend strength, Y is the coverage gap, area is search volume
  (`scaleSqrt`), color is lifecycle. The top-right region is tinted as the whitespace quadrant. Positions are exact:
  bubbles overlap rather than being moved. Labels use a greedy placement (`placeLabels`): for each trend in priority
  order (selected, highlighted, largest gap) try above, right, left and below, and keep the first position that stays
  inside the plot and overlaps no placed label; a second pass allows overlapping a neighboring bubble (labels have a
  halo) but never another label. Unplaced names appear in the tooltip.
* **Agent highlight.** Highlighted trends get a pulsing ring and everything else fades to 13% opacity; a chip clears
  it. This is how a reply that names five trends shows them on the map.
* **Demand chart** (`LineChart`). Monotone curves, a history line drawn in with an animated `pathLength`, a gradient
  area, a dashed forecast with a widening confidence band, a hover read-out and brush-to-zoom (drag selects a range,
  double-click resets). The same component draws one trend with its band or three trends overlaid.
* **Ridgeline timeline** (`Viz.tsx::Timeline`). All 24 curves as overlapping areas ordered by peak week, with today and
  the forecast zone marked.
* **Brand-fit heatmap** (`Viz.tsx::Heatmap`). Cell color is `color-mix` of the primary color into the surface color by
  fit; coverage is a bar; a brand header re-sorts.
* **Trend poster.** The detail header is tinted from the trend's lead swatch. `luminance()` chooses white or dark text.
  A fabric texture (`Texture.tsx`: twill, rib, weave, bouclé) is drawn as an SVG pattern at low opacity, and the poster
  opens as a circle growing from the clicked bubble (`clipPath: circle()` from the click position).
* **Garments.** Product and trend images are flat SVG silhouettes (`Garment.tsx`) because the frame cannot load images.
* **Count-up numbers** use Motion's `animate`. **Reduced motion** is honored in the base CSS.

## 8. Theming

The full explanation is [THEMING.md](THEMING.md); this is the summary.

`lib/tokens.css` defines every color as a custom property: a Google blue ramp, neutrals, status colors and the
lifecycle palette. `[data-theme="dark"]` swaps the values. Gemini Enterprise does not pass its theme to the frame, so the
page has its own toggle (the moon button), and components use tokens such as `--on-accent` and `--tip-bg` instead of
fixed colors, which keeps contrast correct in both themes.

## 9. Time limits

Gemini Enterprise stops waiting for an agent after a while and shows "the connection to the server was lost". One model
call took about 100 seconds in testing. Two limits keep the agent inside the window:

* `MODEL_CALL_TIMEOUT_MS` (40 s) times out one model call, with up to three attempts (`agent.py`).
* `TURN_TIMEOUT_S` (85 s) bounds the whole turn (`executor.execute`); on expiry the agent replies that it stopped and
  suggests asking again or narrowing the question.

## 10. Testing

| Test | Checks |
|---|---|
| `test_state.py` | dataset shape and determinism, KPI definitions, the one-shot note, state size, click parsing |
| `test_tools.py` | every tool's function declaration builds; filters, sorting, resolution; canvas and board changes; recommendation format; the new views |
| `test_canvas.py` | the canvas messages pass the catalog validator; the page carries the state and the CSP meta; each render is a new surface; the frame height |
| `test_executor.py` | click reading (structured context, separators), routing, the open turn's part order, the workspace state in the click message, the turn timeout |

Also useful:

* `make screenshots` renders every view from the production bundle with the same state the agent injects.
* `scripts/chat.py` talks to the agent over A2A and prints the reply and the canvas state, locally or deployed.
* `scripts/ge_client.py` sends a turn through Gemini Enterprise's own API. A click is simulated with
  `--action-as text` and no positional text: that endpoint accepts only text parts, and Gemini Enterprise joins all text
  parts into one, so extra text in front of the `Selected:` line prevents the click from matching.
* The browser's DevTools shows the real Canvas element size and the frame's DOM.

## 11. Deployment and registration

`make deploy` builds the image from source (the Dockerfile builds the page first, then the Python service), deploys it
to Cloud Run as a private service with a dedicated service account, pins `APP_URL` to the stable URL that contains the
project number (Gemini Enterprise checks the agent card host), and grants the Discovery Engine service agent the invoker
role. `make register` builds the agent card from `card.py` with that URL and creates or updates the agent in the Gemini
Enterprise app. Because Gemini Enterprise keeps a static copy of the card, run it again after any card change.

## 12. Gemini Enterprise behaviors the design depends on

| Behavior | Consequence in the design |
|---|---|
| The frame is sandboxed (`allow-scripts`), with no network and no navigation | All data is in the page; links live outside the frame |
| `IFrameSrcdoc.height` is pixels only; the Canvas panel does not scroll | A fixed-height app shell with an internal scroll region |
| Only `a2ui_action` messages leave the frame; `data.prompt` becomes the user's message | Every action carries the state and a readable prompt |
| An update-only message to an open Canvas is not applied | Each reply creates a new surface; state carries continuity |
| Messages sent while the agent is `working` appear under "Show thinking" | The surface is attached to the closing artifact |
| One A2UI message is limited to 1 MiB | The page and its state stay near 0.6 MB; a test checks the limit |
| `createSurface` must name the composite catalog, and the card must list it in `supportedCatalogIds` | `kit/sdk.py` and `card.py` |
| The API endpoint for testing accepts only text parts | Clicks are simulated as a `Selected:` line |
| GE stops waiting for a slow agent | Model-call and turn time limits |

## 13. Adapting it

1. **Replace the data.** Return the same dict shape from `catalog.dataset()` or change the shape and update `trends.ts`.
2. **Replace the tools.** Keep the pattern: read tools return compact data; write tools set `ui_state` and call
   `request_update`.
3. **Replace the views.** Keep the shell (`TrendsScene.tsx`), the components (`components.tsx`) and the bridge; build the
   views from them. Everything must live in the injected state.
4. **Keep the contract.** Every action posts the state; every reply renders from the state; the instruction states what
   the user is looking at; the click message repeats it.
5. **Check the limits.** State plus page under 1 MiB; tool declarations build; canvas messages validate; the turn ends
   inside the time budget.
6. **Move state out of memory** (a shared store keyed by user) before running more than one instance.
