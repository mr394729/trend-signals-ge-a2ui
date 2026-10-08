# Agentic workspace: a Pattern 3 page driven by an agent (A2UI v0.9, Gemini Enterprise)

A workspace is a custom HTML page in the Canvas side panel and an agent in the chat that share one state. The user
works in the page; the agent analyzes, answers and changes what the page shows. This reference describes the design
and the Gemini Enterprise behaviors it depends on. The Trend Signals blueprint implements it end to end.

## Contents

1. The design in one page
2. Frame and layout: an app shell
3. State: both directions
4. The agent
5. The page build
6. Visualization
7. Time limits
8. Testing
9. Checklist
10. Earlier approach and why it was replaced

## 1. The design in one page

```
Canvas > IFrameSrcdoc (fixed height) > page (app shell, all data inline)
   ^                                        |
   | new Canvas surface per reply           | postMessage {type:'a2ui_action', action, data:{...state, prompt}}
   |                                        v
 agent service  <------ A2A turn: prompt + action context (the state) ------ Gemini Enterprise
   ui_state (view, selection, board, filters, highlights, recommendations, note)
```

- The page is sealed: no network, no navigation. It receives its data and state in the HTML.
- Interactions that do not need the agent (tabs, filters, drill-down, chart hover, selection) are client state.
- An interaction that needs the agent posts an action. `data.prompt` becomes the user's message; the rest of `data` is
  the action context, and it carries the page's state.
- The agent cannot update an open Canvas. It renders the page again with the state it chose and sends a new Canvas
  surface; Gemini Enterprise reopens the panel with it.

## 2. Frame and layout: an app shell

Facts that shape the layout:

- `IFrameSrcdoc.height` is a number of pixels. There is no "fill the panel" option and no resize message.
- The Canvas panel does not scroll its content. A frame shorter than the panel leaves empty space below it; a frame
  taller than the panel is cut off, and a long page inside it cannot be scrolled to its end.

Build the page as an application shell in a fixed-height frame:

```html
<div class="flex h-dvh flex-col">                    <!-- exactly the frame height -->
  <div class="shrink-0"> header, tabs, filters </div>   <!-- stays put -->
  <main class="min-h-0 flex-1 overflow-y-auto pb-20"> view </main>   <!-- scrolls -->
</div>
```

- Use one fixed frame height that fits a laptop-height panel (for example 1024). The page fills it whatever the
  content, and the scrolling happens inside.
- Give the scrolling region bottom padding. If the frame is a little taller than the panel, only the padding is cut off.
- Do not size the frame from the user's screen height: the page cannot see the panel, and the first render has no
  information.
- Do not use a long page with `min-height: 100vh` as the document scroller: the frame is fixed, so the page is either
  cut off or has a gap.

## 3. State: both directions

Define one state object that the server builds and the page types. Typical parts: the data, the view state, what the
agent wrote into the page (recommendations, a one-shot note), and suggestion chips.

### Page to agent

- Every action posts the whole view state next to the prompt: view, selected item, comparison, board, filters, highlights,
  scroll offset of the content region. Send values as strings; keep separators out of the keys.
- On the server, read the structured action context rather than the flattened `Selected: name; k=v` line: the line cannot
  carry values that contain `;` or `=`.
- Store the state per conversation (the A2A `contextId`), or per user only when the user comes from a verified
  credential; never from message metadata, which the caller sets.
- State the view in the model's input, not only in the system instruction. In a long conversation the model weights earlier
  turns; a message that ends with `[Workspace right now: view=detail; selected: X]` keeps "this" pointing at what the user
  has open.
- Typed chat messages carry no state; the agent uses the state of the last action. Say so in the instruction.

### Agent to page

- Tools that change what the user sees write to the same state (view, selection, filters, highlights, a note) and set a flag.
- After the model's final response, render the page from the state and attach the surface to the closing artifact (or the
  `completed` status). A surface attached to a `working` update appears under "Show thinking".
- Reset the scroll offset when the agent navigates to a different view or item; keep it when it re-renders the same one,
  and restore it when the page mounts.
- Highlight, do not filter, when the reply names items: dim the rest and show a chip that clears it.

State held in memory is per instance: run one instance, or keep the state in a shared store keyed by user.

## 4. The agent

- Read tools return compact data: rows with the numbers the model needs, not whole records.
- Write tools take simple parameters. For structured items, accept delimited strings and reject malformed ones with a message
  the model can act on; this avoids open-ended object schemas in the function declaration.
- Test the declaration of every tool (`FunctionTool(fn)._get_declaration()`); an unsupported signature fails in CI.
- Instruction: state the domain and metrics, the workspace and its views, when to use each tool, when to highlight, and the reply
  format: call all tools first and write one reply after the last call, lead with the answer and numbers, say what changed on
  the canvas, end with one next step, never show internal ids.
- Open the workspace with a deterministic path (a greeting or an "open" phrase); no model call is needed.

## 5. The page build

- React and Vite with `vite-plugin-singlefile`: one `index.html`, everything inline. Add `connect-src 'none'` as a CSP meta element
  at build time; Gemini Enterprise removes it and applies its own policy.
- Inject state before `</head>` as a script that assigns a window variable, and escape every `</` in the JSON.
- Useful stack: Tailwind v4 over custom properties, Radix primitives for tabs, selects, toggles, tooltips and dialogs, d3 scales and
  shapes rendered as SVG, Motion for animation, Lucide for icons, cmdk for a command palette. Import Tailwind's utilities into a CSS
  layer and keep other CSS inside layers: unlayered CSS beats layered utilities.
- Images are not available. Draw illustrations and textures as SVG.
- Keep the page and state well under the 1 MiB limit of one A2UI data part (a page of about 0.5 MB with 70 KB of state is fine).
- Dev mode: load a fixture exported from the server's data so the page can be designed without the agent.

## 6. Visualization

- Draw charts as SVG with d3 scales. Keep data positions exact; use opacity and placement for overlap rather than moving points.
- Label placement: place labels in priority order and keep the first of above, right, left and below that stays in the plot and overlaps
  no placed label; unplaced items appear in a tooltip.
- Forecast: solid history, dashed forecast, a band that widens with the horizon, a hover read-out, drag to zoom and double-click to reset.
- Encode a category with a color and a label; do not rely on color alone.
- Other forms that worked: a heatmap (items against categories with `color-mix` cells), a ridgeline timeline ordered by peak, a poster header
  tinted from an item's own palette with a luminance check for text color, SVG textures, count-up numbers and a circular reveal.
- Honor `prefers-reduced-motion`. Provide a theme toggle: Gemini Enterprise does not pass its theme to the frame.

## 7. Time limits

Gemini Enterprise stops waiting for a slow agent and shows "your connection to the server was lost". A single model call took about
100 seconds in testing. Set a timeout on each model call with retries (for example 40 seconds and three attempts) and a budget for the
whole turn (for example 85 seconds); on expiry, reply that the agent stopped and suggest asking again or narrowing the question.

## 8. Testing

- Unit tests: state building, click parsing with separators, routing, tool behavior, tool declarations, the order of parts in the open reply,
  the turn timeout.
- Validate every canvas message against the composite catalog (`Surface.messages` does this), and check the size against 1 MiB.
- Render every view from the production bundle with the injected state and look at it, at a wide and a narrow width and in both themes.
- Talk to the agent over A2A (a script that prints the reply and the canvas state) and through Gemini Enterprise's per-agent endpoint. That
  endpoint accepts only text parts: simulate a click as a `Selected:` line with no other text, because Gemini Enterprise joins all text parts
  into one and an extra prompt in front stops the line from matching.
- Use the browser's DevTools on the real Canvas to see the panel and frame sizes.

## 9. Checklist

- [ ] Fixed frame height; the page is an app shell with one scrolling region and bottom padding.
- [ ] One state object, typed on both sides, under the size limit.
- [ ] Every action carries the view state and a readable `prompt`; the server reads the structured context.
- [ ] The model's input states what the user has open; the instruction says typed messages carry no state.
- [ ] Tools that change the view write the shared state; the page is rendered after the reply and attached to the closing artifact.
- [ ] Each reply creates a new Canvas surface; scroll is restored only for the same view.
- [ ] Model-call and turn time limits are set.
- [ ] Surfaces validate against the catalog; tool declarations build; views were rendered and inspected.
- [ ] Workspace state is shared across instances, or the service runs one instance.

## 10. Earlier approach and why it was replaced

| | Earlier: long page | Workspace: app shell |
|---|---|---|
| Layout | A long document in a frame; the frame height was a guess | A fixed frame with pinned header and a scrolling region |
| Outcome in the Canvas | Blank space below a short frame, or content that could not be scrolled to | Fills the frame; scrolls inside |
| Actions | Carried only their own values (a clicked item, a form) | Carry the whole view state and a readable prompt |
| Agent | Answered with a card; the page did not change with the conversation | Changes the page: view, highlights, recommendations, a note |
| Agent's knowledge of the page | None between actions | The state of the last action, and the exact view in each action's message |
| Navigation | Mostly agent turns | Local state; agent turns only when the agent is needed |
| Visuals | Hand-written HTML and CSS, one theme | Component library, SVG charts, animation, light and dark themes |
| Time limits | None | Per model call and per turn |
