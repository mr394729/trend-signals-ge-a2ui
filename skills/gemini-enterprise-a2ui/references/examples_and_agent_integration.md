# Blueprints and agent integration (A2UI v0.9, Gemini Enterprise)

Complete message lists that validate against the composite catalog, and Python code for emitting and
receiving A2UI in A2A and ADK agents. Validate changes with `scripts/validate_a2ui.py` (it reads the
`json` blocks in this file).

Every blueprint uses the composite catalog:
`https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json`.

## Blueprint 1: KPI card with VegaChart, MaterialTable and SplitButton

An inline analytical card: KPI tiles, a Vega-Lite line chart, a static table and actions.

```json
[
  {"version": "v0.9", "createSurface": {"surfaceId": "supply-chain-summary", "catalogId": "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json"}},
  {"version": "v0.9", "updateDataModel": {"surfaceId": "supply-chain-summary", "path": "/", "value": {"selectedExportAction": "export_pdf"}}},
  {"version": "v0.9", "updateComponents": {"surfaceId": "supply-chain-summary", "components": [
    {"id": "root", "component": "MaterialCard", "appearance": "outlined", "children": ["main_col"]},
    {"id": "main_col", "component": "MaterialColumn", "align": "stretch", "style": {"gap": "16px", "padding": "16px"},
     "children": ["header_row", "div_top", "kpi_row", "trend_chart", "facility_table", "div_bottom", "footer_row"]},
    {"id": "header_row", "component": "MaterialRow", "align": "center", "style": {"gap": "8px"}, "children": ["header_icon", "header_title"]},
    {"id": "header_icon", "component": "MaterialIcon", "icon": "precision_manufacturing", "color": "primary"},
    {"id": "header_title", "component": "MaterialText", "text": "Plant yield and lead-time monitor", "usageHint": "h3"},
    {"id": "div_top", "component": "MaterialDivider"},
    {"id": "kpi_row", "component": "MaterialRow", "justify": "spaceBetween", "align": "stretch", "style": {"gap": "12px"}, "children": ["kpi_1", "kpi_2", "kpi_3"]},
    {"id": "kpi_1", "component": "MaterialColumn", "weight": 1, "style": {"padding": "12px", "borderRadius": "8px", "backgroundColor": "#F8F9FA"}, "children": ["kpi_1_label", "kpi_1_val"]},
    {"id": "kpi_1_label", "component": "MaterialText", "text": "Average yield", "usageHint": "caption"},
    {"id": "kpi_1_val", "component": "MaterialText", "text": "94.2% (-1.8%)", "usageHint": "h3"},
    {"id": "kpi_2", "component": "MaterialColumn", "weight": 1, "style": {"padding": "12px", "borderRadius": "8px", "backgroundColor": "#F8F9FA"}, "children": ["kpi_2_label", "kpi_2_val"]},
    {"id": "kpi_2_label", "component": "MaterialText", "text": "At-risk shipments", "usageHint": "caption"},
    {"id": "kpi_2_val", "component": "MaterialText", "text": "3 lots ($1.42M)", "usageHint": "h3"},
    {"id": "kpi_3", "component": "MaterialColumn", "weight": 1, "style": {"padding": "12px", "borderRadius": "8px", "backgroundColor": "#F8F9FA"}, "children": ["kpi_3_label", "kpi_3_val"]},
    {"id": "kpi_3_label", "component": "MaterialText", "text": "Mean recovery time", "usageHint": "caption"},
    {"id": "kpi_3_val", "component": "MaterialText", "text": "14.5 hours", "usageHint": "h3"},
    {"id": "trend_chart", "component": "VegaChart", "height": 260, "spec": {
      "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
      "data": {"values": [
        {"week": "W36", "plant": "Plant A", "yield": 96.4}, {"week": "W37", "plant": "Plant A", "yield": 95.8},
        {"week": "W38", "plant": "Plant A", "yield": 91.2}, {"week": "W36", "plant": "Plant B", "yield": 97.1},
        {"week": "W37", "plant": "Plant B", "yield": 96.9}, {"week": "W38", "plant": "Plant B", "yield": 97.2}]},
      "mark": {"type": "line", "point": true, "tooltip": true},
      "encoding": {
        "x": {"field": "week", "type": "ordinal", "title": "Week"},
        "y": {"field": "yield", "type": "quantitative", "title": "Yield (%)", "scale": {"domain": [88, 100]}},
        "color": {"field": "plant", "type": "nominal", "title": "Plant"}}}},
    {"id": "facility_table", "component": "MaterialTable",
     "columns": [{"header": "Plant", "field": "plant"}, {"header": "Lot", "field": "lot"}, {"header": "Yield", "field": "yield"}, {"header": "Target", "field": "target"}, {"header": "Status", "field": "status"}],
     "rows": [
       {"plant": "Plant A", "lot": "LOT-8841", "yield": "91.2%", "target": "95.0%", "status": "Excursion"},
       {"plant": "Plant B", "lot": "LOT-8842", "yield": "97.2%", "target": "95.0%", "status": "Nominal"}]},
    {"id": "div_bottom", "component": "MaterialDivider"},
    {"id": "footer_row", "component": "MaterialRow", "justify": "end", "align": "center", "style": {"gap": "12px"}, "children": ["remediate_btn", "export_split_btn"]},
    {"id": "remediate_btn", "component": "MaterialButton", "label": "Start root-cause analysis", "appearance": "filled", "leadingIcon": "build_circle",
     "action": {"event": {"name": "launch_rca", "context": {"prompt": "Run a root-cause analysis on LOT-8841 at Plant A", "lotId": "LOT-8841"}}}},
    {"id": "export_split_btn", "component": "SplitButton", "variant": "stroked", "color": "primary", "value": {"path": "/selectedExportAction"},
     "primaryOption": {"label": "Export brief (PDF)", "value": "export_pdf"},
     "options": [{"label": "Export lot data (CSV)", "value": "export_csv"}, {"label": "Create slides", "value": "export_slides"}],
     "action": {"event": {"name": "export_artifact", "context": {"prompt": "Export the LOT-8841 brief", "format": {"path": "/selectedExportAction"}, "lotId": "LOT-8841"}}}}
  ]}}
]
```

Follow-up chips for this turn go in a separate suggestions part (see section 6.3), not in the card.

## Blueprint 2: Canvas side panel with Stepper and an IFrameSrcdoc simulator

A root `Canvas` renders an opener card in the chat and its children in the side panel. The frame posts
an `a2ui_action` with a `prompt` back to the agent.

```json
[
  {"version": "v0.9", "createSurface": {"surfaceId": "remediation-canvas", "catalogId": "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json"}},
  {"version": "v0.9", "updateComponents": {"surfaceId": "remediation-canvas", "components": [
    {"id": "root", "component": "Canvas", "cardTitle": "Recovery plan and what-if simulator", "cardDescription": "Transfer simulator and execution tracker", "cardIcon": "tune", "autoOpen": true, "autoFullscreen": false, "children": ["canvas_col"]},
    {"id": "canvas_col", "component": "MaterialColumn", "align": "stretch", "style": {"gap": "16px", "padding": "16px"}, "children": ["canvas_heading", "workflow_stepper", "div_sim", "sim_iframe"]},
    {"id": "canvas_heading", "component": "MaterialText", "text": "Remediation steps", "usageHint": "h3"},
    {"id": "workflow_stepper", "component": "Stepper", "activeStep": 1, "steps": [
      {"title": "Isolate the anomaly", "helpText": "Completed: pressure drift identified", "status": "completed"},
      {"title": "Allocate buffer stock", "helpText": "In progress: choose a quantity in the simulator", "status": "in_progress", "selected": true, "child": "step2_detail"},
      {"title": "Dispatch carrier", "helpText": "Pending buffer confirmation", "status": "pending"}]},
    {"id": "step2_detail", "component": "MaterialText", "text": "Use the simulator below to compare expedite cost with penalties avoided.", "usageHint": "body2"},
    {"id": "div_sim", "component": "MaterialDivider"},
    {"id": "sim_iframe", "component": "IFrameSrcdoc", "title": "Transfer simulator", "height": 340,
     "htmlContent": "<style>body{font-family:system-ui,sans-serif;margin:0;padding:16px;background:#f8fafc;color:#1e293b}.card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px}.row{display:flex;justify-content:space-between;margin:12px 0}.val{font-weight:700;color:#1a73e8}button{width:100%;margin-top:12px;padding:10px;border:none;border-radius:8px;background:#1a73e8;color:#fff;font-weight:600}@media (prefers-color-scheme:dark){body{background:#1f1f1f;color:#e3e3e3}.card{background:#2a2a2a;border-color:#444}}</style><div class='card'><label for='q'>Transfer volume: <span id='qOut'>250</span> units</label><input id='q' type='range' min='50' max='500' step='25' value='250' style='width:100%' oninput='update()'><div class='row'><span>Expedite cost</span><span class='val' id='cost'>$37,500</span></div><div class='row'><span>Penalty avoided</span><span class='val' id='save'>$312,500</span></div><button onclick='commit()'>Send plan to the agent</button></div><script>function update(){var q=+document.getElementById('q').value;document.getElementById('qOut').textContent=q;document.getElementById('cost').textContent='$'+(q*150).toLocaleString();document.getElementById('save').textContent='$'+(q*1250).toLocaleString();}function commit(){var q=+document.getElementById('q').value;window.parent.postMessage({type:'a2ui_action',action:'commit_transfer',data:{prompt:'Commit a transfer of '+q+' units',units:q}},'*');}</script>"}
  ]}}
]
```

On later turns, send the surface again with `createSurface` and the current content, under a new
`surfaceId`; the side panel reopens with the current state. In testing in October 2026, an update-only
message to a Canvas opened in an earlier turn was not applied in the Gemini Enterprise UI.

## Blueprint 3: Validated form with two-way binding

Seed defaults, bind inputs, validate, and disable submit until the fields are valid.

```json
[
  {"version": "v0.9", "createSurface": {"surfaceId": "purchase-order-form", "catalogId": "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json", "sendDataModel": true}},
  {"version": "v0.9", "updateDataModel": {"surfaceId": "purchase-order-form", "path": "/orderForm", "value": {
    "supplierCode": "SUP-409", "quantity": 250, "priorityTier": "expedited",
    "startDate": {"year": 2026, "month": 10, "day": 10}, "deliveryDate": {"year": 2026, "month": 10, "day": 18}, "notifyWarehouse": true}}},
  {"version": "v0.9", "updateComponents": {"surfaceId": "purchase-order-form", "components": [
    {"id": "root", "component": "MaterialCard", "appearance": "outlined", "children": ["form_col"]},
    {"id": "form_col", "component": "MaterialColumn", "align": "stretch", "style": {"gap": "14px", "padding": "16px"},
     "children": ["form_title", "supplier_input", "qty_input", "tier_select", "date_row", "notify_toggle", "live_summary", "form_divider", "submit_row"]},
    {"id": "form_title", "component": "MaterialText", "text": "Replenishment order", "usageHint": "h3"},
    {"id": "supplier_input", "component": "MaterialInput", "label": "Supplier ID (SUP-XXX)", "value": {"path": "/orderForm/supplierCode"}, "checks": [
      {"condition": {"call": "required", "args": {"value": {"path": "/orderForm/supplierCode"}}, "returnType": "boolean"}, "message": "Supplier ID is required."},
      {"condition": {"call": "regex", "args": {"value": {"path": "/orderForm/supplierCode"}, "pattern": "^SUP-[0-9]{3,5}$"}, "returnType": "boolean"}, "message": "Use the format SUP-409."}]},
    {"id": "qty_input", "component": "MaterialInput", "label": "Quantity (50 to 1,000)", "type": "number", "value": {"path": "/orderForm/quantity"}, "checks": [
      {"condition": {"call": "numeric", "args": {"value": {"path": "/orderForm/quantity"}, "min": 50, "max": 1000}, "returnType": "boolean"}, "message": "Enter 50 to 1,000 units."}]},
    {"id": "tier_select", "component": "MaterialSelect", "label": "Logistics tier", "value": {"path": "/orderForm/priorityTier"}, "options": [
      {"label": "Standard (7 to 10 days)", "value": "standard"}, {"label": "Expedited air (48 hours)", "value": "expedited"}, {"label": "Courier (24 hours)", "value": "critical"}]},
    {"id": "date_row", "component": "MaterialRow", "style": {"gap": "12px"}, "children": ["start_date_picker", "delivery_date_picker"]},
    {"id": "start_date_picker", "component": "MaterialDatepicker", "weight": 1, "label": "Dispatch date", "value": {"path": "/orderForm/startDate"}},
    {"id": "delivery_date_picker", "component": "MaterialDatepicker", "weight": 1, "label": "Delivery date", "value": {"path": "/orderForm/deliveryDate"}, "checks": [
      {"condition": {"call": "dateIsBeforeOrEqual", "args": {"a": {"path": "/orderForm/startDate"}, "b": {"path": "/orderForm/deliveryDate"}}, "returnType": "boolean"}, "message": "Delivery must be on or after dispatch."}]},
    {"id": "notify_toggle", "component": "MaterialSlideToggle", "label": "Notify the receiving warehouse", "color": "primary", "checked": {"path": "/orderForm/notifyWarehouse"}},
    {"id": "live_summary", "component": "MaterialText", "usageHint": "caption", "text": {"call": "formatString",
      "args": {"value": "${/orderForm/quantity} units from ${/orderForm/supplierCode}, ${/orderForm/priorityTier} logistics."}, "returnType": "string"}},
    {"id": "form_divider", "component": "MaterialDivider"},
    {"id": "submit_row", "component": "MaterialRow", "justify": "end", "children": ["authorize_btn"]},
    {"id": "authorize_btn", "component": "MaterialButton", "label": "Authorize order", "appearance": "filled", "leadingIcon": "verified",
     "disabled": {"call": "not", "args": {"value": {"call": "areComponentsValid", "args": {"componentIds": ["supplier_input", "qty_input", "delivery_date_picker"]}, "returnType": "boolean"}}, "returnType": "boolean"},
     "action": {"event": {"name": "authorize_purchase_order", "context": {
       "prompt": "Authorize the replenishment order",
       "supplierCode": {"path": "/orderForm/supplierCode"}, "quantity": {"path": "/orderForm/quantity"},
       "priorityTier": {"path": "/orderForm/priorityTier"}, "notifyWarehouse": {"path": "/orderForm/notifyWarehouse"}}}}}
  ]}}
]
```

## Blueprint 4: Map with a route and a place card

```json
[
  {"version": "v0.9", "createSurface": {"surfaceId": "logistics-route-map", "catalogId": "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json"}},
  {"version": "v0.9", "updateComponents": {"surfaceId": "logistics-route-map", "components": [
    {"id": "root", "component": "MaterialCard", "appearance": "outlined", "children": ["map_col"]},
    {"id": "map_col", "component": "MaterialColumn", "align": "stretch", "style": {"gap": "12px", "padding": "16px"}, "children": ["map_title", "route_map", "hub_place_card"]},
    {"id": "map_title", "component": "MaterialText", "text": "Cold-chain transit corridor", "usageHint": "h3"},
    {"id": "route_map", "component": "GoogleMap", "center": {"lat": 35.6812, "lng": 139.7671}, "zoom": 11, "mode": "roadmap", "travelMode": "driving",
     "markers": [
       {"lat": 35.6812, "lng": 139.7671, "label": "Distribution hub", "placeId": "ChIJ51cu8IcbXWARiRtXIothAS4", "placePrimaryType": "retail"},
       {"lat": 35.5494, "lng": 139.7798, "label": "Cargo terminal", "placePrimaryType": "airport"}],
     "routes": [{"origin": {"lat": 35.5494, "lng": 139.7798, "label": "Cargo terminal"}, "destination": {"lat": 35.6812, "lng": 139.7671, "label": "Distribution hub"}}]},
    {"id": "hub_place_card", "component": "PlaceDetailsCompact", "placeId": "ChIJ51cu8IcbXWARiRtXIothAS4", "orientation": "horizontal"}
  ]}}
]
```

## Blueprint 5: InteractiveChart and RichTable

These components are built on Conversational Analytics. The payload shape below validates against the
catalog; confirm it renders in your Gemini Enterprise app before relying on it, and prefer `VegaChart`
and `MaterialTable` for general use.

```json
[
  {"version": "v0.9", "createSurface": {"surfaceId": "bi-explorer-card", "catalogId": "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json"}},
  {"version": "v0.9", "updateComponents": {"surfaceId": "bi-explorer-card", "components": [
    {"id": "root", "component": "MaterialCard", "appearance": "outlined", "children": ["bi_col"]},
    {"id": "bi_col", "component": "MaterialColumn", "align": "stretch", "style": {"gap": "16px", "padding": "16px"}, "children": ["bi_title", "studio_chart", "studio_table"]},
    {"id": "bi_title", "component": "MaterialText", "text": "Revenue by region", "usageHint": "h3"},
    {"id": "studio_chart", "component": "InteractiveChart", "chartData": {"title": "Revenue by region", "spec": {"barChart": {}},
      "schema": [{"name": "region", "dataType": "STRING"}, {"name": "revenue", "dataType": "DOUBLE"}],
      "data": [{"region": "North America", "revenue": 1420000}, {"region": "EMEA", "revenue": 980000}, {"region": "APAC", "revenue": 1150000}]}},
    {"id": "studio_table", "component": "RichTable", "tableData": {
      "schema": [{"name": "region", "dataType": "STRING"}, {"name": "revenue", "dataType": "DOUBLE"}, {"name": "growth_pct", "dataType": "DOUBLE"}],
      "data": [{"region": "North America", "revenue": 1420000, "growth_pct": 14.2}, {"region": "EMEA", "revenue": 980000, "growth_pct": 6.8}, {"region": "APAC", "revenue": 1150000, "growth_pct": -2.1}]}}
  ]}}
]
```

## 6. Agent integration (Python)

### 6.1 The public A2UI Agent SDK

The public A2UI Agent SDK (`pip install a2ui-agent-sdk`, Python package `a2ui`; the examples below use
version 0.7.0) provides the agent card extension, the A2A parts, catalog validation, and a prompt
generator and parser for model-written A2UI. Bind it to a local copy of the composite catalog once:

```python
from a2ui.inference_formats.direct_json import DirectJsonFormat
from a2ui.schema.catalog import CatalogConfig
from a2ui.schema.constants import VERSION_0_9

COMPOSITE_CATALOG = (
    "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/"
    "gemini_enterprise_composite_catalog.json"
)
A2UI_FORMAT = DirectJsonFormat(VERSION_0_9, catalogs=[CatalogConfig.from_path(
    name="gemini_enterprise_composite", catalog_path="ge_composite_catalog_v0_9.json")])
CATALOG = A2UI_FORMAT.get_selected_catalog()
```

The SDK does not cover three Gemini Enterprise specifics, so agents add them:

- **Final-event attachment.** Attach A2UI parts to the closing artifact or the `completed` status update.
  ADK's A2A executor sends the model's final response as a `working` update first, and Gemini Enterprise
  shows `working` parts under "Show thinking" (SKILL.md section 12).
- **Suggestions.** Build the follow-up chips part yourself (section 6.3).
- **Object-valued properties.** The catalog types `VegaChart.spec`, `InteractiveChart.chartData`, `RichTable.tableData`, `GdfForm.initialPayload` and five `WebAppFrameUrl` properties as the common `DynamicValue`. In the SDK's v0.9
  common types, `DynamicValue` has no object form, so the SDK validator rejects object values that Gemini
  Enterprise renders. Load the catalog through your own `A2uiCatalogProvider` (passed as
  `CatalogConfig(name=..., provider=...)`) whose `load()` rewrites every component property whose `$ref` ends
  with `common_types.json#/$defs/DynamicValue` to `{"anyOf": [{"$ref": ...}, {"type": "object"}]}`. Basic and
  Material components still reject undeclared properties.

SDK validation builds the catalog schema for each component it checks: expect about 30 ms per component
(about 2 seconds for a 68-component card).

### 6.2 Agent card extension

```python
from a2ui.a2a.extension import get_a2ui_agent_extension

a2ui_extension = get_a2ui_agent_extension(
    VERSION_0_9, accepts_inline_catalogs=False, supported_catalog_ids=[COMPOSITE_CATALOG])
```

The resulting entry in `capabilities.extensions` (the SDK omits `acceptsInlineCatalogs` when it is `false`,
its default):

```json
{
  "uri": "https://a2ui.org/a2a-extension/a2ui/v0.9",
  "description": "Provides agent driven UI using the A2UI JSON format.",
  "params": {"supportedCatalogIds": ["https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json"]}
}
```

Register the card in Gemini Enterprise, and update the Agent resource after any card change; Gemini
Enterprise keeps its own copy.

### 6.3 Emitting A2UI messages as A2A parts

Each message is its own `DataPart` with the mime type `application/json+a2ui`; the SDK's
`create_a2ui_part` uses that mime type for v0.8 and v0.9 messages. Put the text reply first, then the A2UI
parts, then an optional suggestions part, all in the final message of the turn. Validate the messages
first: `CATALOG.validate` raises a `ValueError` subclass for an unknown component, an undeclared property, a
value outside its schema, a missing `root` or a dangling child ID.

```python
from a2a.types import DataPart, Part, TextPart
from a2ui.a2a.parts import create_a2ui_part

SUGGESTIONS_MIME_TYPE = "application/json+suggestions"


def response_parts(text: str, a2ui_messages: list[dict], suggestions: list[str]) -> list[Part]:
    CATALOG.validate(a2ui_messages)
    parts = [Part(root=TextPart(text=text))]
    parts += [create_a2ui_part(m) for m in a2ui_messages]
    if suggestions:
        parts.append(Part(root=DataPart(
            data={"recommendedQuestionsResponse": {
                "suggestions": [{"question": q[:85], "FollowUpQuestionMetadata": {"sourceType": "A2A_AGENT"}}
                                for q in suggestions[:3]],
                "questions": [q[:85] for q in suggestions[:3]]}},
            metadata={"mimeType": SUGGESTIONS_MIME_TYPE})))
    return parts
```

Send these parts once, in the final status update or in the closing artifact, not both; Gemini
Enterprise stores every A2UI part it receives.

### 6.4 Model-written A2UI (Pattern 1)

The SDK's prompt generator writes a system instruction with the A2UI rules and the catalog schemas of the
components you allow; the model answers with text and an `<a2ui-json>` block. Parse with the SDK's parser
directly: it raises on a missing or malformed block, while `parse_content_to_parts` logs the error and
drops the block. Validate, add the rules the schema cannot express, and give the model one repair round.

```python
ALLOWED = ["Card", "Column", "Row", "Text", "Button"]
system_instruction = A2UI_FORMAT.prompt_generator.generate(
    role_description="You answer plant questions with a short reply and one A2UI v0.9 card.",
    ui_description="Reply first, then one <a2ui-json> block with createSurface and updateComponents. "
                   "The root is a Card. Every Button has action.event.context.prompt.",
    allowed_components=ALLOWED, include_schema=True)


def parse_and_validate(raw: str) -> tuple[str, list[dict]]:
    texts, messages = [], []
    for part in A2UI_FORMAT.parser.parse_response(raw):  # raises A2uiParseError (a ValueError)
        if part.text and part.text.strip():
            texts.append(part.text.strip())
        if part.a2ui_json:
            messages += part.a2ui_json if isinstance(part.a2ui_json, list) else [part.a2ui_json]
    CATALOG.validate(messages)                           # raises A2uiValidationError (a ValueError)
    for c in (c for m in messages for c in (m.get("updateComponents") or {}).get("components") or []):
        if c["component"] not in ALLOWED:
            raise ValueError(f"{c['component']} is not allowed")
    return "\n\n".join(texts), messages
```

On a `ValueError`, send the model's answer back as a model turn and the error as a user turn, and ask for
a corrected block. If the second answer is invalid too, send the text answer with a note that the card
could not be shown. `scripts/validate_a2ui.py` is a dependency-free alternative for offline checks.

### 6.5 Server-composed cards (Pattern 2)

Let tools decide what to show and build the card in code from the tool result:

```python
def order_card(order: dict, surface_id: str) -> list[dict]:
    return [
        {"version": "v0.9", "createSurface": {"surfaceId": surface_id, "catalogId": COMPOSITE_CATALOG}},
        {"version": "v0.9", "updateComponents": {"surfaceId": surface_id, "components": [
            {"id": "root", "component": "MaterialCard", "children": ["col"]},
            {"id": "col", "component": "MaterialColumn", "style": {"gap": "8px", "padding": "16px"}, "children": ["t", "s", "b"]},
            {"id": "t", "component": "MaterialText", "text": f"Order {order['id']}", "usageHint": "h3"},
            {"id": "s", "component": "MaterialText", "text": f"**{order['qty']}** units, {order['tier']}"},
            {"id": "b", "component": "MaterialButton", "label": "Approve", "appearance": "filled",
             "action": {"event": {"name": "approve_order",
                                  "context": {"prompt": f"Approve order {order['id']}", "orderId": order["id"]}}}},
        ]}},
    ]
```

### 6.6 Receiving clicks and form submissions

A click arrives as a text part (the prompt) and a `DataPart` with the action envelope:

```python
def incoming_action(parts: list) -> dict | None:
    for part in parts:
        root = getattr(part, "root", part)
        data = getattr(root, "data", None)
        if isinstance(data, dict) and data.get("version") == "v0.9" and "action" in data:
            return data["action"]  # {name, surfaceId, sourceComponentId, timestamp, context}
        if isinstance(data, dict) and data.get("version") == "v0.9" and "error" in data:
            log.warning("render error reported by the user: %s", data["error"])
    return None
```

Handle data-bearing actions (save, submit) in code, then pass the prompt to the model as the user's
words so the conversation continues naturally.

### 6.7 Google Search grounding display

If the answer used Grounding with Google Search, attach the model's grounding metadata to the final
status update so Gemini Enterprise renders the Google Search entry point:

```python
def grounding_metadata(response) -> dict | None:
    gm = response.candidates[0].grounding_metadata
    if gm is None:
        return None
    data = gm.model_dump(mode="json", exclude_none=True)
    return {k: data[k] for k in ("search_entry_point", "web_search_queries", "grounding_chunks") if k in data}

# On the final TaskStatusUpdateEvent:
# event.metadata = {**(event.metadata or {}), "grounding_metadata": grounding_metadata(resp)}
```

### 6.8 Progress during long turns

With `capabilities.streaming: true`, text in `working` status updates appears as "Thinking" progress,
for example "Researching three companies". The answer itself must be in the final `completed` update.
