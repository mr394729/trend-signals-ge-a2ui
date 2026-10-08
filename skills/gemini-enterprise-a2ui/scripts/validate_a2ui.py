#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Offline validator for Gemini Enterprise A2UI (v0.9) payloads.

Errors (the payload would be rejected):
1. v0.9 message envelopes (createSurface, updateComponents, updateDataModel,
   deleteSurface), including keys createSurface does not accept.
2. Surface topology: a component with id "root", flat adjacency list, no
   dangling child/header/trigger/content/step references, no duplicate IDs.
3. Component schemas from the bundled composite catalog
   (resources/gemini_enterprise_composite_catalog.json): known components,
   required properties, no unknown properties.
4. Legacy v0.8 constructs (beginRendering, literalString, explicitList,
   wrapped component objects, child on MaterialCard).
5. Canvas literal properties and the cardIcon pattern.
6. Client-side function calls against the registered functions.
7. The camelCase style allowlist.

Warnings (accepted, but Gemini Enterprise renders it differently):
- markdown in a Basic Text with an h1-h5 or caption variant (shown literally)
- labels on TextField, ChoicePicker and DateTimeInput (not displayed)
- ChoicePicker.filterable (ignored), Stepper step description (ignored)
- actions without context.prompt ("User action triggered." in the chat)
- IFrameSrcdoc without height (4:3 box) or with links (blocked by the sandbox)

Usage:
  python3 scripts/validate_a2ui.py path/to/payload.json
  python3 scripts/validate_a2ui.py path/to/notes.md      # json and <a2ui-json> blocks
  cat payload.json | python3 scripts/validate_a2ui.py -
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import pathlib
import re
import sys
from typing import Any
import urllib.request

COMPOSITE_CATALOG_URL = (
    "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/"
    "gemini_enterprise_composite_catalog.json"
)

SUPPORTED_CATALOG_IDS = {
    COMPOSITE_CATALOG_URL,
    "https://a2ui.org/specification/v0_9/material_catalog.json",
    "https://a2ui.org/specification/v0_9/basic_catalog.json",
}

ENVELOPE_COMMANDS = {"createSurface", "updateComponents", "updateDataModel", "deleteSurface"}
CREATE_SURFACE_KEYS = {"surfaceId", "catalogId", "sendDataModel"}

V08_LEGACY_KEYS = {
    "beginRendering", "surfaceUpdate", "dataModelUpdate",
    "literalString", "literalNumber", "literalBoolean", "explicitList",
}

CANVAS_LITERAL_PROPS = {"cardTitle", "cardDescription", "cardIcon", "autoOpen", "autoFullscreen"}
CARD_ICON_RE = re.compile(r"^[a-z0-9_]{1,64}$")
A2UI_BLOCK_RE = re.compile(r"<a2ui-json>\s*(.*?)\s*</a2ui-json>", re.DOTALL)
MARKDOWN_RE = re.compile(r"\*\*|__|\[[^\]]+\]\(|`|^#|^\s*[-*] ", re.M)
NON_MARKDOWN_TEXT_VARIANTS = {"h1", "h2", "h3", "h4", "h5", "caption"}
COMMON_KEYS = {"id", "component", "accessibility"}


class ValidationResult:
  """Accumulates validation errors and warnings."""

  def __init__(self) -> None:
    self.errors: list[str] = []
    self.warnings: list[str] = []

  def error(self, location: str, message: str) -> None:
    self.errors.append(f"[ERROR] {location}: {message}")

  def warn(self, location: str, message: str) -> None:
    self.warnings.append(f"[WARN]  {location}: {message}")

  @property
  def ok(self) -> bool:
    return not self.errors


def load_catalog_schema(catalog_path: pathlib.Path | None = None) -> dict[str, Any]:
  """Loads the bundled composite catalog, or downloads it next to the script if missing."""
  if catalog_path is None:
    script_dir = pathlib.Path(__file__).resolve().parent
    target = script_dir.parent / "resources" / "gemini_enterprise_composite_catalog.json"
    if not target.is_file():
      target.parent.mkdir(parents=True, exist_ok=True)
      with urllib.request.urlopen(COMPOSITE_CATALOG_URL, timeout=10) as resp:
        target.write_text(resp.read().decode("utf-8"), encoding="utf-8")
    catalog_path = target
  return json.loads(catalog_path.read_text(encoding="utf-8"))


def _flat_properties(schema: dict[str, Any]) -> dict[str, Any]:
  """Properties of a schema, including those nested in allOf entries."""
  props = dict(schema.get("properties", {}))
  for entry in schema.get("allOf", []):
    props.update(entry.get("properties", {}))
  return props


def extract_catalog_rules(catalog: dict[str, Any]) -> dict[str, Any]:
  """Extracts component, function and style rules from the composite catalog."""
  defs = catalog.get("$defs", {})
  mat_common = _flat_properties(defs.get("MaterialComponentCommon", {}))
  custom_common = _flat_properties(defs.get("CustomComponentCommonProps", {}))
  cat_common = _flat_properties(defs.get("CatalogComponentCommon", {}))
  allowed_styles = set(mat_common.get("style", {}).get("properties", {}).keys())

  components_spec: dict[str, dict[str, Any]] = {}
  for comp_name, comp_schema in catalog.get("components", {}).items():
    props: dict[str, Any] = {}
    required: set[str] = {"id", "component"}
    allowed: set[str] = set(COMMON_KEYS)
    supports_style = False
    for entry in comp_schema.get("allOf", []) + [comp_schema]:
      ref = entry.get("$ref", "")
      if ref.endswith("/MaterialComponentCommon"):
        allowed |= set(mat_common)
        supports_style = True
      elif ref.endswith("/CustomComponentCommonProps"):
        allowed |= set(custom_common)
      elif ref.endswith("/CatalogComponentCommon"):
        allowed |= set(cat_common)
      elif ref.endswith("/Checkable"):
        allowed.add("checks")
      props.update(entry.get("properties", {}))
      required.update(entry.get("required", []))
    allowed |= set(props)
    components_spec[comp_name] = {
        "allowed_keys": allowed,
        "required_keys": required,
        "properties": props,
        "supports_style": supports_style or "style" in props,
    }

  functions_spec: dict[str, dict[str, Any]] = {}
  for fn_name, fn_schema in catalog.get("functions", {}).items():
    args_schema = fn_schema.get("properties", {}).get("args", {})
    functions_spec[fn_name] = {
        "returnType": fn_schema.get("properties", {}).get("returnType", {}).get("const"),
        "required_args": set(args_schema.get("required", [])),
        "allowed_args": set(args_schema.get("properties", {}).keys()),
    }
  return {"components": components_spec, "functions": functions_spec, "allowed_styles": allowed_styles}


def find_legacy_v08_keys(obj: Any, path: str, result: ValidationResult) -> None:
  if isinstance(obj, dict):
    for k, v in obj.items():
      if k in V08_LEGACY_KEYS:
        result.error(f"{path}.{k}", f"A2UI v0.8 key '{k}' is not valid in v0.9.")
      find_legacy_v08_keys(v, f"{path}.{k}", result)
  elif isinstance(obj, list):
    for idx, item in enumerate(obj):
      find_legacy_v08_keys(item, f"{path}[{idx}]", result)


def validate_function_calls(obj: Any, path: str, functions_spec: dict[str, dict[str, Any]],
                            referenced_ids: list[tuple[str, str]], result: ValidationResult) -> None:
  if isinstance(obj, dict):
    if isinstance(obj.get("call"), str):
      fn_name = obj["call"]
      if fn_name not in functions_spec:
        result.error(path, f"Unknown client function '{fn_name}'. Allowed: {sorted(functions_spec)}")
      else:
        rule = functions_spec[fn_name]
        args = obj.get("args", {})
        if not isinstance(args, dict):
          result.error(f"{path}.args", "'args' must be an object.")
        else:
          missing = rule["required_args"] - set(args)
          if missing:
            result.error(f"{path}.args", f"'{fn_name}' is missing args {sorted(missing)}.")
          unknown = set(args) - rule["allowed_args"]
          if unknown:
            result.error(f"{path}.args", f"'{fn_name}' has unknown args {sorted(unknown)}.")
          if fn_name == "areComponentsValid" and isinstance(args.get("componentIds"), list):
            for cid in args["componentIds"]:
              if isinstance(cid, str):
                referenced_ids.append((f"{path}.args.componentIds", cid))
    for k, v in obj.items():
      validate_function_calls(v, f"{path}.{k}", functions_spec, referenced_ids, result)
  elif isinstance(obj, list):
    for idx, item in enumerate(obj):
      validate_function_calls(item, f"{path}[{idx}]", functions_spec, referenced_ids, result)


def collect_child_references(comp: dict[str, Any], comp_path: str,
                             referenced_ids: list[tuple[str, str]], result: ValidationResult) -> None:
  for key in ("child", "header", "trigger", "content"):
    if key in comp:
      if isinstance(comp[key], str):
        referenced_ids.append((f"{comp_path}.{key}", comp[key]))
      else:
        result.error(f"{comp_path}.{key}", f"'{key}' must be a component ID string.")
  children = comp.get("children")
  if isinstance(children, list):
    for idx, cid in enumerate(children):
      if isinstance(cid, str):
        referenced_ids.append((f"{comp_path}.children[{idx}]", cid))
      else:
        result.error(f"{comp_path}.children[{idx}]",
                     "Children must be component ID strings; define components in the flat list.")
  elif isinstance(children, dict):
    if set(children) != {"path", "componentId"} or not isinstance(children.get("componentId"), str):
      result.error(f"{comp_path}.children", "A template must be exactly {'path', 'componentId'}.")
    else:
      referenced_ids.append((f"{comp_path}.children.componentId", children["componentId"]))
  elif children is not None:
    result.error(f"{comp_path}.children", "'children' must be a list of IDs or a template.")
  for idx, tab in enumerate(comp.get("tabs") or []):
    if isinstance(tab, dict):
      for tk in ("content", "child"):
        if isinstance(tab.get(tk), str):
          referenced_ids.append((f"{comp_path}.tabs[{idx}].{tk}", tab[tk]))
  for idx, step in enumerate(comp.get("steps") or []):
    if isinstance(step, dict) and "child" in step:
      if isinstance(step["child"], str):
        referenced_ids.append((f"{comp_path}.steps[{idx}].child", step["child"]))
      else:
        result.error(f"{comp_path}.steps[{idx}].child", "Step 'child' must be a component ID string.")


def rendering_warnings(comp: dict[str, Any], loc: str, result: ValidationResult) -> None:
  """Properties that validate but render differently in Gemini Enterprise."""
  ctype = comp.get("component")
  if ctype == "Text" and comp.get("variant") in NON_MARKDOWN_TEXT_VARIANTS:
    text = comp.get("text")
    if isinstance(text, str) and MARKDOWN_RE.search(text):
      result.warn(loc, f"Text with variant '{comp['variant']}' shows markdown literally; use MaterialText.")
  if ctype == "ChoicePicker" and comp.get("filterable"):
    result.warn(loc, "ChoicePicker.filterable is ignored.")
  if ctype == "Stepper":
    for idx, step in enumerate(comp.get("steps") or []):
      if isinstance(step, dict) and "description" in step:
        result.warn(f"{loc}.steps[{idx}]", "Step description is ignored; use helpText or child.")
  if ctype == "IFrameSrcdoc":
    if "height" not in comp:
      result.warn(loc, "IFrameSrcdoc without height renders as a 4:3 box.")
    html = comp.get("htmlContent")
    if isinstance(html, str) and re.search(r"<a\s[^>]*href=|window\.open\(", html):
      result.warn(loc, "Links and window.open are blocked in IFrameSrcdoc; render links outside the frame.")


def validate_messages(messages: list[Any], rules: dict[str, Any]) -> ValidationResult:
  """Validates a sequence of A2UI v0.9 messages."""
  result = ValidationResult()
  components_spec, functions_spec = rules["components"], rules["functions"]
  allowed_styles = rules["allowed_styles"]
  created: set[str] = set()
  surface_components: dict[str, set[str]] = defaultdict(set)
  surface_references: dict[str, list[tuple[str, str]]] = defaultdict(list)
  label_fields: list[tuple[str, Any, str, str]] = []
  prev_sibling: dict[tuple[str, str], str | None] = {}
  comp_types: dict[tuple[str, str], str] = {}

  for idx, msg in enumerate(messages):
    loc = f"message[{idx}]"
    if not isinstance(msg, dict):
      result.error(loc, f"Message must be an object, got {type(msg).__name__}.")
      continue
    find_legacy_v08_keys(msg, loc, result)
    if msg.get("version") != "v0.9":
      result.error(loc, f"'version' must be 'v0.9', got {msg.get('version')!r}.")
    commands = [k for k in msg if k in ENVELOPE_COMMANDS]
    extra = set(msg) - ENVELOPE_COMMANDS - {"version"}
    if extra:
      result.error(loc, f"Unknown top-level keys {sorted(extra)}.")
    if len(commands) != 1:
      result.error(loc, f"Each message needs exactly one of {sorted(ENVELOPE_COMMANDS)}, found {commands}.")
      continue
    cmd = commands[0]
    payload = msg[cmd]
    cmd_loc = f"{loc}.{cmd}"
    if not isinstance(payload, dict):
      result.error(cmd_loc, f"'{cmd}' must be an object.")
      continue
    sid = payload.get("surfaceId")
    if not isinstance(sid, str) or not sid:
      result.error(cmd_loc, "'surfaceId' is required.")
      sid = "<unknown>"

    if cmd == "createSurface":
      cid = payload.get("catalogId")
      if not isinstance(cid, str) or not cid:
        result.error(cmd_loc, "'catalogId' is required.")
      elif cid not in SUPPORTED_CATALOG_IDS:
        result.warn(cmd_loc, f"catalogId '{cid}' is not a standard Gemini Enterprise catalog.")
      bad = set(payload) - CREATE_SURFACE_KEYS
      if bad:
        result.error(cmd_loc, f"createSurface accepts only {sorted(CREATE_SURFACE_KEYS)}; remove {sorted(bad)}.")
      created.add(sid)
    elif cmd == "updateDataModel":
      bad = set(payload) - {"surfaceId", "path", "value"}
      if bad:
        result.error(cmd_loc, f"Unknown keys in updateDataModel: {sorted(bad)}.")
    elif cmd == "deleteSurface":
      bad = set(payload) - {"surfaceId"}
      if bad:
        result.error(cmd_loc, f"Unknown keys in deleteSurface: {sorted(bad)}.")
    elif cmd == "updateComponents":
      if sid not in created:
        result.warn(cmd_loc, f"No createSurface for '{sid}' in this batch; it must already exist on the client.")
      comps = payload.get("components")
      if not isinstance(comps, list) or not comps:
        result.error(f"{cmd_loc}.components", "'components' must be a non-empty list.")
        continue
      seen: set[str] = set()
      for c_idx, comp in enumerate(comps):
        c_loc = f"{cmd_loc}.components[{c_idx}]"
        if not isinstance(comp, dict):
          result.error(c_loc, "Component must be an object.")
          continue
        comp_id, comp_type = comp.get("id"), comp.get("component")
        if not isinstance(comp_id, str) or not comp_id:
          result.error(c_loc, "Component needs a string 'id'.")
        else:
          if comp_id in seen:
            result.error(c_loc, f"Duplicate component id '{comp_id}'.")
          seen.add(comp_id)
          surface_components[sid].add(comp_id)
        if isinstance(comp_type, dict):
          result.error(f"{c_loc}.component", "'component' must be a type name string, not a v0.8 wrapper.")
          continue
        if not isinstance(comp_type, str) or not comp_type:
          result.error(c_loc, "Component needs a string 'component'.")
          continue
        c_loc = f"{cmd_loc}.components[{c_idx}](id={comp_id!r}, {comp_type})"
        if comp_type not in components_spec:
          result.error(c_loc, f"Unknown component type '{comp_type}'.")
          continue
        spec = components_spec[comp_type]
        missing = spec["required_keys"] - set(comp)
        if missing:
          result.error(c_loc, f"Missing required properties {sorted(missing)}.")
        unknown = set(comp) - spec["allowed_keys"]
        if unknown:
          hint = ""
          if comp_type == "MaterialCard" and "child" in unknown:
            hint = " MaterialCard uses 'children'; Basic Card uses 'child'."
          elif "style" in unknown:
            hint = f" '{comp_type}' does not accept 'style'; use a Material component."
          result.error(c_loc, f"Unknown properties {sorted(unknown)}.{hint}")
        if comp_type == "Canvas":
          if comp_id != "root":
            result.error(c_loc, "Canvas must be the root component (id 'root').")
          for lp in CANVAS_LITERAL_PROPS:
            if isinstance(comp.get(lp), dict):
              result.error(f"{c_loc}.{lp}", f"Canvas '{lp}' must be a literal.")
          icon = comp.get("cardIcon")
          if isinstance(icon, str) and not CARD_ICON_RE.match(icon):
            result.error(f"{c_loc}.cardIcon", f"cardIcon {icon!r} must match ^[a-z0-9_]{{1,64}}$.")
        if comp_type == "MaterialInput" and comp.get("type") == "password":
          result.error(f"{c_loc}.type", "MaterialInput type 'password' is not allowed.")
        if "style" in comp and spec["supports_style"]:
          if not isinstance(comp["style"], dict):
            result.error(f"{c_loc}.style", "'style' must be an object.")
          else:
            bad_styles = set(comp["style"]) - allowed_styles
            if bad_styles:
              result.error(f"{c_loc}.style", f"Style keys not in the allowlist: {sorted(bad_styles)}.")
        if "action" in comp:
          act = comp["action"]
          if not isinstance(act, dict) or ("event" not in act and "functionCall" not in act):
            result.error(f"{c_loc}.action", "'action' needs 'event' or 'functionCall'.")
          elif "event" in act:
            ev = act["event"]
            if not isinstance(ev, dict) or not isinstance(ev.get("name"), str):
              result.error(f"{c_loc}.action.event", "'action.event' needs a string 'name'.")
            elif not isinstance(ev.get("context"), dict) or "prompt" not in ev["context"]:
              result.warn(f"{c_loc}.action.event.context",
                          "No 'prompt': the chat shows \"User action triggered.\".")
          else:
            result.warn(f"{c_loc}.action", "functionCall actions still start an agent turn in Gemini Enterprise.")
        rendering_warnings(comp, c_loc, result)
        if comp_type in ("TextField", "ChoicePicker", "DateTimeInput") and comp.get("label"):
          label_fields.append((sid, comp_id, comp_type, c_loc))
        if isinstance(comp.get("children"), list):
          for i, child in enumerate(comp["children"]):
            if isinstance(child, str):
              prev_sibling[(sid, child)] = comp["children"][i - 1] if i else None
        if isinstance(comp_id, str):
          comp_types[(sid, comp_id)] = comp_type
        collect_child_references(comp, c_loc, surface_references[sid], result)
        validate_function_calls(comp, c_loc, functions_spec, surface_references[sid], result)

  for sid, comp_ids in surface_components.items():
    if "root" not in comp_ids and sid in created:
      result.error(f"surface[{sid!r}]", 'No component with "id": "root".')
    for ref_loc, target in surface_references[sid]:
      if target not in comp_ids:
        result.error(ref_loc, f"Component '{target}' is not defined in surface '{sid}'.")

  for sid, comp_id, comp_type, c_loc in label_fields:
    prev = prev_sibling.get((sid, comp_id))
    if comp_types.get((sid, prev)) not in ("MaterialText", "Text"):
      result.warn(c_loc, f"{comp_type}.label is not displayed; put a MaterialText label before it or use a Material input.")

  size = len(json.dumps(messages))
  if size > 1024 * 1024:
    result.error("batch", f"{size} bytes; each A2UI DataPart must stay under 1 MiB.")
  return result


def parse_input_text(raw_text: str) -> list[tuple[str, list[Any]]]:
  """Message batches from JSON, JSONL, <a2ui-json> blocks or ```json blocks in Markdown."""
  batches: list[tuple[str, list[Any]]] = []
  for idx, match in enumerate(A2UI_BLOCK_RE.finditer(raw_text)):
    block = match.group(1).strip()
    if not block.startswith(("{", "[")):
      continue  # prose or code that mentions the tag
    parsed = json.loads(block)
    batches.append((f"<a2ui-json>[{idx}]", parsed if isinstance(parsed, list) else [parsed]))
  stripped = raw_text.strip()
  if not stripped.startswith(("{", "[")):
    for idx, match in enumerate(re.finditer(r"```json\s*(.*?)\s*```", raw_text, re.DOTALL)):
      try:
        parsed = json.loads(match.group(1).strip())
      except json.JSONDecodeError:
        continue
      msgs = parsed if isinstance(parsed, list) else [parsed]
      if msgs and isinstance(msgs[0], dict) and "version" in msgs[0] and any(
          k in msgs[0] for k in ENVELOPE_COMMANDS):
        batches.append((f"json_block[{idx}]", msgs))
    return batches
  if batches:
    return batches
  try:
    parsed = json.loads(stripped)
    return [("root", parsed if isinstance(parsed, list) else [parsed])]
  except json.JSONDecodeError:
    return [("jsonl", [json.loads(line) for line in stripped.splitlines() if line.strip()])]


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(description="Validate Gemini Enterprise A2UI v0.9 payloads.")
  parser.add_argument("inputs", nargs="+", help=".json, .jsonl or .md files, or '-' for stdin")
  parser.add_argument("--catalog", type=pathlib.Path, default=None, help="path to the composite catalog JSON")
  parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
  args = parser.parse_args(argv)

  rules = extract_catalog_rules(load_catalog_schema(args.catalog))
  overall_ok, total = True, 0
  for inp in args.inputs:
    raw = sys.stdin.read() if inp == "-" else pathlib.Path(inp).read_text(encoding="utf-8")
    label = "<stdin>" if inp == "-" else inp
    try:
      batches = parse_input_text(raw)
    except json.JSONDecodeError as exc:
      print(f"[ERROR] {label}: invalid JSON: {exc}")
      overall_ok = False
      continue
    for name, msgs in batches:
      total += 1
      res = validate_messages(msgs, rules)
      for line in res.errors + res.warnings:
        print(f"{label} ({name}) {line}")
      if res.ok and not (args.strict and res.warnings):
        print(f"[PASS]  {label} ({name}): {len(msgs)} message(s)")
      else:
        overall_ok = False
  if total == 0:
    print("[ERROR] No A2UI v0.9 messages found.")
    return 1
  return 0 if overall_ok else 1


if __name__ == "__main__":
  sys.exit(main())
