---
name: gemini-enterprise-a2ui
description: Designs, authors, validates and integrates A2UI v0.9 interfaces for Gemini Enterprise agents. Use when building A2UI JSON payloads; rendering cards, forms, tables, charts, maps, steppers or Canvas side panels in Gemini Enterprise; embedding sandboxed HTML with IFrameSrcdoc, including agent-driven workspaces in the Canvas; wiring data bindings, validation and actions; adding suggestion chips or Google Search grounding display; registering an A2A agent in Gemini Enterprise; testing it through the API; or migrating A2UI v0.8 surfaces to v0.9. Covers verified Gemini Enterprise rendering behaviour that differs from the schema, such as labels and markdown that are not rendered.
metadata:
  version: "1.0"
  verified: "2026-10-01"
  a2ui: "v0.9"
allowed-tools: Bash Read Write Edit
---

# Gemini Enterprise A2UI (v0.9)

A2UI lets an agent describe interface as JSON: a flat list of components, a reactive data model and
actions. The agent sends A2UI messages next to its text reply over A2A; Gemini Enterprise renders them
with its own components, in the chat or in the Canvas side panel, and returns user interactions to the
agent as structured actions.

This skill combines the A2UI v0.9 schema with Gemini Enterprise behaviour verified in its renderer and
backend. Where the schema and the renderer disagree, this skill follows the renderer (section 4).

## When to use

- Writing or reviewing A2UI v0.9 messages for a Gemini Enterprise agent.
- Choosing components for a job: input, review and submit, tables, charts, maps, workflows, side panels.
- Building server code that emits A2UI from an ADK or A2A agent, or handles clicks and form submissions.
- Registering an agent in Gemini Enterprise, or testing it through the API.
- Diagnosing "Couldn't display this content", missing labels, raw markdown, missing suggestion chips,
  blocked links or lost text.

## References

| File | Contents |
|---|---|
| [references/component_catalog.md](references/component_catalog.md) | Every public component in the composite catalog, with properties and rendering notes |
| [references/functions_and_styling.md](references/functions_and_styling.md) | The client-side functions, validation `checks`, and the `style` allowlist |
| [references/examples_and_agent_integration.md](references/examples_and_agent_integration.md) | Complete message blueprints and Python ADK / A2A integration code |
| [references/theming_tailwind_radix.md](references/theming_tailwind_radix.md) | Styling a Canvas page: design tokens, Tailwind v4 theme mapping, Radix components, a Google Cloud look, light and dark themes |
| [references/agentic_workspace.md](references/agentic_workspace.md) | A Pattern 3 workspace driven by an agent: app-shell layout, state in both directions, time limits, testing |
| [scripts/validate_a2ui.py](scripts/validate_a2ui.py) | Validates a message list against the composite catalog and the tree rules |

## 1. Catalog and agent card

Every surface binds to one catalog in `createSurface.catalogId`. Use the composite catalog:

`https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json`

It merges the Material catalog, the A2UI Basic catalog, the Gemini Enterprise custom components
(`Canvas`, `VegaChart`, `IFrameSrcdoc`, `Stepper` and others) and the Google Maps components. The URL is
versioned only at the protocol level (`v0_9`); components are added in place. Validate against the
current file before relying on a property.

The agent card must declare the A2UI extension with the composite catalog in `supportedCatalogIds`.
Without it, Gemini Enterprise reports "Catalog not found". Gemini Enterprise does not accept inline
catalogs.

```json
{
  "capabilities": {
    "streaming": true,
    "extensions": [{
      "uri": "https://a2ui.org/a2a-extension/a2ui/v0.9",
      "description": "Renders A2UI v0.9",
      "params": {
        "supportedCatalogIds": ["https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json"],
        "acceptsInlineCatalogs": false
      }
    }]
  }
}
```

With the public A2UI Agent SDK (`a2ui-agent-sdk`), `get_a2ui_agent_extension(VERSION_0_9,
accepts_inline_catalogs=False, supported_catalog_ids=[<composite catalog URL>])` produces this entry; it
omits `acceptsInlineCatalogs` when it is `false`. See references/examples_and_agent_integration.md section 6.

## 2. Messages

Each message is a JSON object with `"version": "v0.9"` and exactly one of `createSurface`,
`updateComponents`, `updateDataModel` or `deleteSurface`. Each message travels as its own A2A
`DataPart` with `metadata.mimeType` set to **`application/json+a2ui`**.

### createSurface

```json
{"version": "v0.9", "createSurface": {"surfaceId": "order-review", "catalogId": "<composite catalog URL>"}}
```

- Accepts only `surfaceId`, `catalogId` and optional `sendDataModel`. There is no `root` and no
  `theme`; any other key fails validation.
- Send it before the first `updateComponents` for that surface. An update for an unknown surface shows
  an error.
- A second `createSurface` with the same ID resets that surface.

### updateComponents

A flat list. One component has `"id": "root"`. Children are referenced by ID, never nested.

```json
{"version": "v0.9", "updateComponents": {"surfaceId": "order-review", "components": [
  {"id": "root", "component": "MaterialCard", "children": ["col"]},
  {"id": "col", "component": "MaterialColumn", "children": ["title", "summary"], "style": {"gap": "12px", "padding": "16px"}},
  {"id": "title", "component": "MaterialText", "text": "Order ORD-402", "usageHint": "h3"},
  {"id": "summary", "component": "MaterialText", "text": {"path": "/summary"}}
]}}
```

### updateDataModel

JSON Pointer paths. Omit `path` (or use `/`) to replace the whole model; omit `value` to delete a key.

```json
{"version": "v0.9", "updateDataModel": {"surfaceId": "order-review", "path": "/summary", "value": "250 units, expedited"}}
```

### deleteSurface

```json
{"version": "v0.9", "deleteSurface": {"surfaceId": "order-review"}}
```

Also closes the Canvas side panel if that surface is open there. Surfaces are never removed
automatically during a conversation.

## 3. Rules that prevent rejection

Every component is validated against a strict schema. One unknown property, or an unknown component,
makes Gemini Enterprise replace the surface with "Couldn't display this content".

| # | Rule | Invalid | Valid |
|---|---|---|---|
| 1 | Version on every message | `{"beginRendering": {...}}` | `{"version": "v0.9", "createSurface": {...}}` |
| 2 | Root is a component with `"id": "root"` | `"createSurface": {"root": "card1"}` | a component `{"id": "root", ...}` |
| 3 | Flat discriminator | `{"component": {"Text": {...}}}` | `{"component": "Text", "text": "Hi"}` |
| 4 | Plain literals | `{"text": {"literalString": "Hi"}}` | `{"text": "Hi"}` or `{"text": {"path": "/msg"}}` |
| 5 | Plain `children` arrays | `{"children": {"explicitList": ["a"]}}` | `{"children": ["a"]}` or `{"path": "/items", "componentId": "tpl"}` |
| 6 | No nested components | `{"children": [{"id": "c1", ...}]}` | `{"children": ["c1"]}`, with `c1` in the list |
| 7 | `MaterialCard` takes `children`; Basic `Card` takes `child` | `{"component": "MaterialCard", "child": "c"}` | `{"component": "MaterialCard", "children": ["c"]}` |
| 8 | `MaterialButton` takes `label`; Basic `Button` takes `child` (a Text ID) | `{"component": "MaterialButton", "child": "t"}` | `{"component": "MaterialButton", "label": "Submit"}` |
| 9 | Server actions are wrapped in `action.event` | `{"action": {"name": "submit"}}` | `{"action": {"event": {"name": "submit", "context": {"prompt": "Submit the order"}}}}` |
| 10 | `style` only on `Material*` components and `MosaicSlideCard`, camelCase, allowlisted keys | `"style"` on `Row`/`Text`; `"background-color"`; `"position"` | `"style": {"backgroundColor": "#F8F9FA", "padding": "16px"}` on `MaterialColumn` |

Run `python scripts/validate_a2ui.py messages.json` before sending new payloads. In an agent that uses
the A2UI Agent SDK, validate each message list with the SDK catalog's `validate` before sending; it checks the
same schemas and the surface tree. Its v0.9 `DynamicValue` has no object form, so object-valued properties such
as `VegaChart.spec` need the correction described in references/examples_and_agent_integration.md section 6.1.

## 4. Verified rendering behaviour

These are properties the schema accepts but the Gemini Enterprise renderer handles differently.

| Area | Behaviour | What to do |
|---|---|---|
| Markdown in Basic `Text` | Rendered only when `variant` is omitted or `body`. With `h1`–`h5` or `caption`, `**`, `#` and `[link](url)` appear as raw characters. | Use `MaterialText`, which renders markdown for every `usageHint`. |
| Labels on Basic inputs | `TextField.label` and `ChoicePicker.label` are not displayed; `DateTimeInput.label` is used only for accessibility. | Use `MaterialInput`, `MaterialSelect`, `MaterialDatepicker`, or put a `MaterialText` label above the field. |
| `TextField.placeholder` | The renderer displays it, but the published catalog does not declare it, so sending it fails validation. | Use `MaterialInput`, which declares `placeholder`. |
| `ChoicePicker.filterable` | Ignored. | For long lists, use `MaterialSelect` or split options into groups. |
| `Stepper` steps | `description` is ignored. In an in-chat card, the Stepper was drawn as a collapsible list with placeholder icons. | Use `helpText` or a `child` component; for progress in a chat card, use a text step line such as "Step 2 of 4 · **Customer & timing**" in `MaterialText`. |
| Links | Markdown links open in a new tab, URL unchanged. | Link sources with markdown in `MaterialText`. |
| Button clicks | Every Button or MaterialButton click starts an agent turn, including `functionCall` actions such as `openUrl`. | For links without a turn, use markdown links, `MaterialCard.href` or a `GcbpTable` `LINK` cell. |
| Repeat clicks | No button disables itself after a click. The renderer has a `MaterialButton` `loadingOnClick` behaviour, but the published catalog does not declare it, so sending it fails validation. | Make submit handlers idempotent on the server, and bind `disabled` where a form state allows it. |
| Unset bound values | A context value bound to an unset path is omitted from the action; `ChoicePicker` writes only when an option is clicked. | Seed defaults with `updateDataModel` before showing a submit button. |
| In-chat surfaces across turns | Each turn keeps a frozen snapshot. An update in a later turn renders in that turn; the earlier card keeps its old state. | Treat each turn's card as a record. |
| Canvas across turns | In testing in October 2026, an update-only message to a Canvas opened in an earlier turn was not applied in the Gemini Enterprise UI. | Send `createSurface` with the full content each turn; the Canvas reopens with the current state. |
| Size | 1 MiB per A2UI DataPart; larger parts are rejected. No component-count limit. | Keep large HTML or datasets under 1 MiB per message. |
| Duplicate parts | The backend stores every A2UI part it receives. | Emit each A2UI part once, in the status message or the artifact, not both. |

## 5. Data binding and forms

- Most properties accept a literal, a binding `{"path": "/a/b"}`, or a function call
  `{"call": "formatString", "args": {...}, "returnType": "string"}`.
- Template children: `{"path": "/orders", "componentId": "order_tpl"}`. Inside the template, relative
  paths (`{"path": "orderId"}`) resolve against the current item; absolute paths against the root.
- Input values write back to the data model as the user edits: `MaterialInput`, `MaterialSelect`,
  `TextField` (string); `MaterialCheckbox`, `MaterialSlideToggle` (`checked`, boolean); `CheckBox`
  (boolean); `MaterialSlider`, `Slider` (number); `ChoicePicker` (string array); `MaterialDatepicker`
  (`{"year", "month", "day"}`, month 1–12); `MaterialTimepicker`, `DateTimeInput` (ISO 8601 string).
- Validation: `checks: [{"condition": <boolean expression>, "message": "..."}]`. Disable submit until
  fields are valid with `not(areComponentsValid(componentIds))`. See
  [functions_and_styling.md](references/functions_and_styling.md).
- Keep a submit button in the same surface as the fields it reads; bindings resolve per surface.
- For several choices on one in-chat card, bind a picker per field and send them with one submit button.
  One Button per option sends a turn per click, and an in-chat card is frozen once its turn ends, so
  only the first click counts.

## 6. Actions and prompts

A click on an action component sends the agent a new turn with:

1. A text part: `action.event.context.prompt` if set, otherwise "User action triggered.". The same text
   appears as the user's chat bubble; they cannot differ. Always set `prompt`.
2. A DataPart (`application/json+a2ui`) with the resolved action:

```json
{"version": "v0.9", "action": {"name": "approve_order", "surfaceId": "order-review",
  "sourceComponentId": "approve_btn", "timestamp": "2026-10-01T12:00:00.000Z",
  "context": {"prompt": "Approve order ORD-402", "orderId": "ORD-402"}}}
```

Put readable text in `prompt` and machine values in other context keys. The turn carries the
conversation's current `contextId`, also for cards from earlier turns, which stay clickable.

## 7. Inline cards and the Canvas side panel

- **Inline**: any root other than `Canvas` renders in the chat under the agent's message.
- **Canvas**: a root `Canvas` component renders an opener card in the chat and its `children` in the
  side panel. `cardTitle`, `cardDescription`, `cardIcon` (lowercase Material Symbols name),
  `autoOpen` and `autoFullscreen` must be literals.
- `autoOpen` defaults to `true`: each new Canvas `surfaceId` opens the panel once, on a live turn.
  Later updates refresh it without reopening. Reloaded conversations do not auto-open.
- Users switch between Canvas surfaces with their opener cards; one is shown at a time.
- The panel docks at 50% (minimum 460 px, about 412 px of content), can be resized to 80% or full
  screen, and is full width on mobile. Design embedded content for 400–1600 px.

## 8. IFrameSrcdoc

- Runs in nested sandboxed frames with `allow-scripts` only. No network (`default-src 'none'`); all
  CSS, JS and images must be inline (`data:` images and fonts). Gemini Enterprise removes any CSP meta
  tag in your HTML and applies its own.
- Links and `window.open` inside the frame are blocked. Render links outside the frame as markdown.
- Height: set `height` in px. Without it the frame is a 4:3 box, also in Canvas. There is no
  auto-resize message and no "fill the panel" option, and the Canvas panel does not scroll its content.
  Use one fixed height (for example 1024) and build the page as an app shell: a pinned header and a content
  region that scrolls inside the frame, with bottom padding (see `references/agentic_workspace.md`).
- The only message the host handles: `window.parent.postMessage({type: 'a2ui_action', action:
  'name', data: {prompt: '...', key: value}}, '*')`. `data` becomes the action context, so
  `data.prompt` becomes the user's bubble text.
- Gemini Enterprise's dark mode is not passed to the frame; `prefers-color-scheme` reflects the OS
  setting only.
- No allow-list is needed for `IFrameSrcdoc`. `IFrameUrl` and `WebAppFrameUrl` require HTTPS and an
  allow-listed hostname.

## 9. Choosing components

| Need | Use |
|---|---|
| Simple static table | `MaterialTable` (`columns: [{header, field}]`, `rows`) |
| Sortable table, link or action cells | `GcbpTable` (Gemini Enterprise component; `columns: [{header, field, sortable}]`; cells can be JSON strings for `BADGE`, `LINK` and `ACTION` content) |
| Charts | `VegaChart` (Vega-Lite 5 `spec`, `height`). Set colours in the spec; Gemini Enterprise inverts the chart in dark mode. |
| Analytics table or chart with Conversational Analytics data | `RichTable`, `InteractiveChart` (`tableData` / `chartData` with `schema` and `data`) |
| Workflow progress | `Stepper` (`steps: [{title, helpText, status, child}]`, `activeStep`); in an in-chat card, a text step line (see section 4) |
| Fixed-list choice | `MaterialSelect`, `MaterialRadioButton`, `MaterialChips`, or `ChoicePicker` with `displayStyle: "chips"` and a separate label |
| Maps and places | `GoogleMap`, `PlaceDetailsCompact` |
| Custom interactive view | `IFrameSrcdoc`, often inside `Canvas` |
| Long or persistent workspace | `Canvas` |

## 10. Three rendering patterns

| Pattern | Source of the UI | Suited to | Consideration |
|---|---|---|---|
| 1. Model-generated | The model writes A2UI from the catalog | Open-ended questions whose layout depends on the answer | Validate before sending; allow one repair round |
| 2. Server-composed | Code builds A2UI from application state | Forms, structured input, records written to systems | One builder per card |
| 3. Custom HTML | Code sends HTML in `IFrameSrcdoc` | Data-dense or custom-designed views, client-side interaction. As a workspace, the page and the agent share one state: actions carry the view state and the agent changes the view (`references/agentic_workspace.md`) | Sandbox limits; more frontend code |

Patterns can be combined in one agent: for example, a model that decides what to show and code that
builds the card from tool results.

## 11. Suggestion chips

Send a DataPart with `metadata.mimeType: "application/json+suggestions"`:

```json
{"recommendedQuestionsResponse": {
  "suggestions": [{"question": "What changed since last week?", "FollowUpQuestionMetadata": {"sourceType": "A2A_AGENT"}}],
  "questions": ["What changed since last week?"]
}}
```

The key must be `recommendedQuestionsResponse` (with "ed"). The backend also accepts
`recommendQuestionsResponse`, but the Gemini Enterprise UI does not display it. The UI reads
`suggestions[].question`; Gemini Enterprise's own assistant sends `questions` (a string list), so send
both. Use up to three
suggestions of up to 85 characters. A row of `MaterialButton` components with `context.prompt` is an
alternative when chips belong inside a card.

## 12. Turn text, progress and streaming

- The visible answer must be in the final status update (`completed`) or the closing artifact.
- The same applies to A2UI parts: attach them to the closing artifact or the `completed` status. Gemini
  Enterprise marks everything in a `working` update as thought, so a card sent there is hidden inside the
  collapsed "Show thinking" section. ADK's A2A executor streams the model's final response as a `working`
  update before the closing artifact, so an event converter that attaches the card on "final response"
  hides it; stash the card and attach it when the closing artifact or `completed` status is sent.
- Text in `working` status updates is shown as "Thinking" progress, not as the answer. Text written
  before a tool call and not repeated in the final message is not part of the visible answer.
- Declare `capabilities.streaming: true` to show progress. The default turn deadline is 1,700 s.

## 13. Google Search grounding

When a response uses Grounding with Google Search, include the model's grounding metadata
(`search_entry_point.rendered_content`, `web_search_queries`, `grounding_chunks`) as
`grounding_metadata` in the metadata of the A2A task, status update, message or part. Gemini Enterprise
then renders the Google Search entry point under the turn, as the grounding display requirements need.
Link individual sources in cards with markdown to the unmodified `grounding_chunks[].web.uri`.

## 14. Identity and OAuth

Gemini Enterprise does not send the user's email to an unauthenticated agent. To act as the user:

1. Create a Discovery Engine `Authorization` resource with `serverSideOauth2` (client ID and secret,
   authorization URI with the scopes, token URI).
2. Reference it from the Agent resource's `authorizationConfig`:
   - `agentAuthorization`: the token arrives as a header (`X-Goog-Agent-User-Authorization` on Cloud
     Run, where `Authorization` carries the invoker's ID token).
   - `toolAuthorizations` plus the card extension
     `https://www.ischolar.dev/a2a/extensions/authorizations/v1`: the token arrives in the request
     metadata under that extension URI.
3. Resolve the email and stable `sub` from the token with the OAuth userinfo or tokeninfo endpoint.

## 15. Registration and the gallery

- Gemini Enterprise stores the agent card JSON at registration and does not re-read
  `/.well-known/agent-card.json`. Update the Agent resource (PATCH) after any card change.
- The backend uses the card's `url`, transports, `description`, `capabilities.streaming`,
  `capabilities.extensions`, `defaultOutputModes` and `provider.url`.
- The agent gallery uses the Agent resource, not the card: `displayName`, `description`,
  `icon.uri`, `starterPrompts: [{"text": ...}]` and `customPlaceholderText`.
- Conversation history: only the messages since the agent's last response are sent, with a stable
  `contextId` per conversation. The `full_history_when_stateless` card extension requests the full
  history when the agent does not return a `contextId`.

## 16. Testing through the API

- Per-agent A2A endpoint:
  `POST .../engines/{engine}/assistants/default_assistant/agents/{agentId}/a2a/v1/message:stream`.
  Send a click as a DataPart (`application/json+a2ui`) with the action envelope, next to a text part
  carrying the prompt. In testing on 2 Oct 2026 this endpoint rejected a data part with `INVALID_ARGUMENT`; it
  accepted text parts only. Simulate a click as one text part, `Selected: <action>; key=value`, with no other
  text, because Gemini Enterprise joins all text parts into one and extra text in front stops the line from matching.
- `streamAssist` accepts `"agentsSpec": {"agentSpecs": [{"agentId": "<agentId>"}]}` and clicks as
  `query.parts` entries (`mimeType: "application/json+a2ui"`, `uiJsonPayload`). In testing on 1 Oct
  2026 such requests were still answered by the default assistant rather than the A2A agent, so check
  the agent's own logs, and prefer the per-agent endpoint above.
- Neither API returns the `grounding_metadata` an agent attaches; check the Google Search entry point in
  the Gemini Enterprise UI.
- A render failure reaches the agent only if the user clicks "Report to agent": the text "User reported
  a render error." and `{"version": "v0.9", "error": {"code", "surfaceId", "path", "message"}}`.

## 17. Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| "Catalog not found" | Card does not list the catalog in `supportedCatalogIds`, or the stored card is outdated | Add it and update the registered Agent resource |
| "Couldn't display this content" | Unknown component or property, update before `createSurface`, broken child reference | Run `validate_a2ui.py`; check "Show details" |
| `**text**` or `[link](url)` shown literally | Basic `Text` with a heading or caption variant | Use `MaterialText` |
| Form fields without labels | Basic `TextField`, `ChoicePicker` or `DateTimeInput` | Use Material inputs or a separate `MaterialText` label |
| Suggestion chips missing | `recommendQuestionsResponse` key | Use `recommendedQuestionsResponse.suggestions` |
| "User action triggered." in the chat | No `context.prompt` (or `data.prompt` from a frame) | Set the prompt |
| Submitted value missing | Bound path never set | Seed defaults with `updateDataModel` |
| Answer text missing | Text sent only in `working` updates or before a tool call | Put the full answer in the final message |
| Card hidden under "Show thinking" | A2UI attached to a `working` update (for example ADK's final-response event) | Attach it to the closing artifact or `completed` status |
| A2UI stored twice | Same parts in the status message and the artifact | Emit once |
| Links in a frame do nothing | Sandbox blocks navigation | Render links as markdown outside the frame |
| Stepper renders as a collapsible list | `Stepper` in an in-chat card | Use a text step line in `MaterialText` |
| Only the first of several choices is saved | One Button per option: each click is a turn, and the earlier card is frozen | Bind a picker per field and send them with one submit button |
| Canvas keeps its first state | Update-only message to a Canvas opened in an earlier turn | Send `createSurface` with the full content each turn |
| Frame cut off in Canvas | No `height`, so 4:3 | Set `height` |
| Blank space below the frame, or the page cannot be scrolled to its end | A long page in a frame of the wrong height; the Canvas panel does not scroll | Fixed frame height and an app-shell page with an internal scrolling region and bottom padding |
| "Your connection to the server was lost" | The agent turn outlasted Gemini Enterprise's wait (one model call took about 100 s) | Time out each model call (about 40 s, with retries) and the whole turn (about 85 s), and reply that the agent stopped |
| The agent answers about the wrong item | Earlier turns outweigh the system instruction | State the open view in the user message of each action |
| Agent card changes ignored | Stored card copy | Update the Agent resource |
| No starter prompts in the gallery | Set only in the card | Set `starterPrompts` on the Agent resource |

## Pre-flight checklist

- [ ] Every message has `"version": "v0.9"` and travels as its own `application/json+a2ui` DataPart.
- [ ] `createSurface` uses the composite catalog and has no `root` or `theme`.
- [ ] Exactly one `"id": "root"` per surface; every referenced child ID exists.
- [ ] No unknown properties; `style` only on `Material*` and `MosaicSlideCard`, with allowlisted keys.
- [ ] Markdown only in `MaterialText` or body `Text`; visible labels for inputs.
- [ ] Every action has `context.prompt`; form defaults are seeded.
- [ ] Each part emitted once, under 1 MiB; final answer text in the final message.
- [ ] Suggestions use `recommendedQuestionsResponse`; grounded answers carry `grounding_metadata`.
- [ ] A Canvas page is an app shell in a fixed-height frame (pinned header, scrolling region, bottom padding); model-call and turn time limits are set.
