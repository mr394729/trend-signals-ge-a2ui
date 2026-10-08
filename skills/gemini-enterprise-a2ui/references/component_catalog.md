# Component catalog reference (A2UI v0.9, Gemini Enterprise)

The public components of the Gemini Enterprise composite catalog
(`https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json`), with
Gemini Enterprise rendering notes. Each component is a flat object in `updateComponents.components`:

```json
{"id": "unique_component_id", "component": "ComponentName", "...": "..."}
```

Schemas are strict: a property not listed for a component fails validation. **Rendering notes** mark
properties that validate but that Gemini Enterprise displays differently.

## Common properties

**Material components** (all `Material*`) accept:

| Property | Type | Description |
|---|---|---|
| `id` | string, required | Unique within the surface; `"root"` for the surface root |
| `component` | string, required | Component name |
| `weight` | number | `flex-grow` inside a flex container |
| `accessibility` | `{label?, description?}` | ARIA label and description |
| `style` | object | Inline CSS, camelCase, allowlisted keys only (see [functions_and_styling.md](functions_and_styling.md)) |

**Gemini Enterprise custom components** accept `id`, `component`, `weight` and `accessibility`; of
these, only `MosaicSlideCard` also accepts `style`.

**Basic components** accept `id`, `component`, `weight` (not applied by the renderer) and
`accessibility`. They do **not** accept `style`: use `MaterialRow`, `MaterialColumn`, `MaterialCard`
and `MaterialText` for styled layout and typography.

## Material components

### Layout and containers

**`MaterialRow`**, **`MaterialColumn`** — flex containers.
- `children` (ChildList, required): IDs, or a template `{"path": "/items", "componentId": "tpl"}`.
- `justify`: `start` | `center` | `end` | `spaceBetween` | `spaceAround` | `spaceEvenly` | `stretch`.
- `align`: `start` | `center` | `end` | `stretch`.

**`MaterialCard`** — card container.
- `children` (ChildList, required). Never `child`.
- `appearance`: `outlined` (default) | `raised`. `align`.
- `href` (DynamicString): the card navigates to this URL when clicked (no agent turn).
- `ariaLabel`, `ariaLabelledby`.

**`MaterialGridList`** — grid.
- `children` (required); `cols` (default 2); `rowHeight` (`"1:1"`, `"200px"`, `"fit"`); `gutterSize`.

**`MaterialDivider`** — `inset`, `vertical`.

**`MaterialExpansionPanel`** — collapsible panel.
- `children` (required); `title`; `description`; `header` (component ID); `expanded` (two-way);
  `disabled`.

**`MaterialTabs`** — tabs, switched locally (no agent turn).
- `children` (IDs of `MaterialTab`) or `tabs: [{label, content}]`; `activeTab` (0-based, two-way).

**`MaterialTab`** — `label` (required), `children` (required).

**`MaterialDialog`** — modal.
- `children` (required); `title`; `trigger` (component ID that opens it); `open`; `disableClose`;
  `width`; `height`.

**`MaterialBadge`** — badge on its children.
- `children` (required); `text` (required); `color` (`primary` | `accent` | `warn`); `position`;
  `size`; `overlap`; `disabled`; `hidden`; `description`.

### Typography, media and data

**`MaterialText`**
- `text` (DynamicString, required); `usageHint`: `h1`–`h5`, `subtitle1`, `subtitle2`, `body`,
  `body1`, `body2`, `caption` (default `body`).
- Rendering: markdown (links, bold, lists, tables, code) is rendered for every `usageHint`. Use this
  instead of Basic `Text` whenever a heading or caption contains markdown.

**`MaterialIcon`** — `icon` (Material Symbols name, required); `color`; `tooltip`.

**`MaterialImage`** — `url` (https or `data:`, required); `alt`; `fit`; `width`; `height`;
`aspectRatio`; `roundedCorners`; `borderRadius`.

**`MaterialProgressBar`** — `value` (0–100); `mode` (`determinate` | `indeterminate` | `buffer` |
`query`); `bufferValue`; `color`.

**`MaterialProgressSpinner`** — `value`; `mode`; `diameter`; `strokeWidth`; `color`.

**`MaterialTable`** — static table; recommended for simple tables.
- `columns: [{header, field}]` (required); `rows` (array of objects keyed by `field`, or a binding,
  required); `caption`; `ariaLabel`.
- Rendering: no sorting, paging, filtering or row actions. Use `GcbpTable` for those.

### Buttons and menus

**`MaterialButton`**
- `label`; `action` (server `event` or `functionCall`); `appearance` (`text` | `filled` |
  `elevated` | `outlined` | `tonal`); `variant`; `color`; `leadingIcon`; `trailingIcon`; `disabled`;
  `tooltip`; `ariaLabel`; `disableRipple`; `extended`.
- Rendering: every click starts an agent turn, including `functionCall` actions. The renderer has a
  `loadingOnClick` behaviour (spinner until the surface updates), but the published catalog does not
  declare it, so it fails validation; make submit handlers idempotent instead.

**`MaterialIconButton`** — `icon` (required); `action` (required); `ariaLabel`; `color`; `disabled`;
`tooltip`.

**`MaterialMenu`** — `options: [{label, value}]` (required); `label`; `icon`; `value` (two-way);
`action`; `disabled`.

### Form controls

All write back to the data model when the value property is bound to a path. Labels on these Material
inputs are displayed.

**`MaterialInput`** — `label`; `placeholder`; `value`; `type` (`text` | `number` | `email` | `tel` |
`date`; `password` is not allowed); `disabled`; `readonly`; `name`; `validationRegexp`; `checks`.

**`MaterialSelect`** — `options` (required); `label`; `placeholder`; `value`; `disabled`; `checks`.

**`MaterialCheckbox`** — `label`; `checked` (boolean); `disabled`; `color`; `labelPosition`;
`tooltip`; `checks`.

**`MaterialRadioButton`** — `options` (required); `value`; `disabled`; `color`; `labelPosition`.

**`MaterialButtonToggle`** — `options` (required); `value`; `appearance`; `vertical`; `disabled`.

**`MaterialChips`** — `options` (required); `value`; `action`; `disabled`.

**`MaterialSlideToggle`** — `label`; `checked`; `disabled`; `color`; `labelPosition`; `tooltip`;
`required`.

**`MaterialSlider`** — `value`; `min` (0); `max` (100); `step` (1); `disabled`; `color`.

**`MaterialDatepicker`** — `label`; `placeholder`; `value` (`{"year", "month", "day"}`, month 1–12);
`disabled`; `checks` (`dateIsBefore`, `dateIsBeforeOrEqual`, `dateEquals`).

**`MaterialTimepicker`** — `label`; `placeholder`; `value` (ISO 8601); `disabled`; `checks`.

## Gemini Enterprise custom components

**`Canvas`** — must be the root. Renders an opener card in the chat and its children in the side panel.
- `children` (required); `cardTitle` (default "Interactive content"); `cardDescription`; `cardIcon`
  (lowercase Material Symbols name, `^[a-z0-9_]{1,64}$`, default `apps`); `autoOpen` (default `true`);
  `autoFullscreen` (default `false`). All five must be literals, not bindings.
- Rendering: `autoOpen` opens the panel once per new `surfaceId` on a live turn. In testing in October
  2026, an update-only message to a Canvas opened in an earlier turn was not applied, so send
  `createSurface` with the full content each turn; the panel reopens with the current state.

**`VegaChart`** — `spec` (Vega-Lite 5 object or binding, required); `height` (px, default 290).
- Rendering: rendered in a sandboxed frame; layers, stacking, facets, transforms and tooltips work.
  Gemini Enterprise overrides `title`, `padding` and `autosize`. Set colours in the spec; parent CSS
  does not reach the chart. Dark mode is applied automatically.

**`InteractiveChart`** — `chartData` (`{title, spec, schema, data}`, required). `schema` entries use
`dataType`: `STRING`, `LONG`, `DOUBLE`, `BOOL`, `DATE`, `DATE_TIME`. Built on Conversational Analytics
components; prefer `VegaChart` for general charts.

**`RichTable`** — `tableData` (`{schema, data}`, required). Filtering, paging and CSV download. Built
on Conversational Analytics components; validate payloads in Gemini Enterprise before relying on them.

**`GcbpTable`** — sortable table with client-side paging (registered in the composite catalog).
- `columns: [{header, field, sortable}]` (required); `rows` (required); `caption`; ARIA properties.
- Cells are strings. A cell can hold a JSON string for structured content, which the renderer parses:
  `{"type": "BADGE", "text", "color"}`, `{"type": "LINK", "text", "url"}` (opens without an agent
  turn), `{"type": "ACTION", "icon", "actionName", "context"}` (dispatches an A2UI action). Verify these
  in your app; server-side paging `metadata` is not in the published catalog.

**`IFrameSrcdoc`** — `htmlContent` (required); `height` (px); `title`.
- Rendering: sandbox `allow-scripts` only; no network; Gemini Enterprise replaces any CSP in the HTML
  with its own (`default-src 'none'`, inline scripts and styles, `data:` images and fonts). Links and
  popups are blocked. Without `height` the frame is 4:3. Only `{type: 'a2ui_action', action, data}`
  messages are handled. Dark mode is not passed in.

**`IFrameUrl`** — `url` (HTTPS, allow-listed hostname, required); `height`; `title`. Same message bridge.
The renderer also supports `themeSync` (appends `?theme=dark|light`), but the published catalog does not
declare it, so sending it fails validation.

**`Stepper`** — `steps: [{title, helpText, status, selected, child}]` (required); `activeStep`
(0-based). `status`: `completed` | `in_progress` | `pending` | `error`. A step `description` is
ignored.

**`SplitButton`** — `primaryOption: {label, value}` (required); `options` (required); `value` (bound
path, required); `action`; `variant`; `color`; `disabled`; `ariaLabel`; `dropdownAriaLabel`. Include
the bound value in `action.event.context`.

**`MosaicSlideCard`** — `deckTitle` (required); `summary`; `thumbnailUrl`; `slideUrl`; `iconUrl`;
`tooltip`; `buttonLabel`; `action`.

## Google Maps components

**`GoogleMap`** — `center: {lat, lng}` (required); `zoom` (required); `mode` (`roadmap` |
`satellite`); `tilt`; `anchorMarker`; `markers: [{lat, lng, label, placeId, placePrimaryType}]`;
`routes: [{origin, destination}]`; `travelMode` (`driving` | `walking` | `bicycling` | `transit`).
`placePrimaryType`: `food_and_drink`, `outdoor`, `retail`, `gas_station`, `ev`, `bank`, `lodging`,
`emergency`, `entertainment`, `airport`, `parking`, `generic`.

**`PlaceDetailsCompact`** — `placeId` (required); `orientation` (`horizontal` | `vertical`).

## Basic components

| Component | Required | Optional | Rendering notes |
|---|---|---|---|
| `Text` | `text` | `variant`: `h1`–`h5`, `caption`, `body` | Markdown rendered only without `variant` or with `body`. With `h1`–`h5` or `caption`, markdown characters show literally. |
| `Image` | `url` | `description`, `fit`, `variant` | |
| `Icon` | `name` (camelCase enum such as `check`, `warning`, `info`, `calendarToday`, or `{"svgPath": ...}`) | | Only the enum names are valid; `MaterialIcon` accepts any Material Symbols name. |
| `Video` | `url` | | |
| `AudioPlayer` | `url` | `description` | |
| `Row`, `Column` | `children` | `justify`, `align` | |
| `List` | `children` | `direction`, `align` | |
| `Card` | `child` (one ID) | | |
| `Tabs` | `tabs: [{title, child}]` | | Switched locally. |
| `Modal` | `trigger`, `content` | | |
| `Divider` | | `axis` | |
| `Button` | `child` (a Text ID), `action` | `variant`: `default` \| `primary` \| `borderless`; `checks` | No repeat-click protection. |
| `TextField` | `label` | `value`, `variant` (`longText`, `number`, `shortText`, `obscured`), `validationRegexp`, `checks` | `label` is not displayed. The renderer reads `placeholder`, but the published catalog does not declare it, so sending it fails validation. |
| `CheckBox` | `label`, `value` | `checks` | |
| `ChoicePicker` | `options`, `value` (string array) | `label`, `variant` (`multipleSelection`, `mutuallyExclusive`), `displayStyle` (`checkbox`, `chips`), `filterable`, `checks` | `label` and `filterable` are ignored. Single-select chips cannot be deselected. |
| `Slider` | `value`, `max` | `min`, `label`, `checks` | |
| `DateTimeInput` | `value` (ISO 8601) | `label`, `enableDate`, `enableTime`, `min`, `max`, `checks` | `label` is used only for accessibility. |
