# Client-side functions and styling (A2UI v0.9, Gemini Enterprise)

Function and style rules of the Gemini Enterprise composite catalog. The function table and the style
allowlist below are generated from the bundled catalog
(`resources/gemini_enterprise_composite_catalog.json`); regenerate them when the catalog changes.

## Function calls

A function call can be used wherever a dynamic value, a `checks` condition or `action.functionCall` is
accepted:

```json
{"call": "functionName", "args": {"arg": "literal, binding or nested call"}, "returnType": "string"}
```

Arguments are evaluated in the browser and re-evaluated when a bound path changes, without an agent
turn.

## Registered functions

`?` marks an optional argument.

| Function | Arguments | Returns | Description |
|---|---|---|---|
| `areComponentsValid` | `componentIds` | `boolean` | Checks if all specified components are valid. |
| `dateIsBeforeOrEqual` | `a`, `b` | `boolean` | Checks if date a is before or equal to date b. |
| `dateIsBefore` | `a`, `b` | `boolean` | Checks if date a is before date b. |
| `dateEquals` | `a`, `b` | `boolean` | Checks if date a is equal to date b. |
| `required` | `value` | `boolean` | Checks that the value is not null, undefined, or empty. |
| `regex` | `value`, `pattern` | `boolean` | Checks that the value matches a regular expression string. |
| `length` | `value`, `min`?, `max`? | `boolean` | Checks string length constraints. |
| `numeric` | `value`, `min`?, `max`? | `boolean` | Checks numeric range constraints. |
| `email` | `value` | `boolean` | Checks that the value is a valid email address. |
| `formatString` | `value` | `string` | Performs string interpolation of data model values and other functions in the catalog functions list and returns the resulting string. |
| `formatNumber` | `value`, `decimals`?, `grouping`? | `string` | Formats a number with the specified grouping and decimal precision. |
| `formatCurrency` | `value`, `currency`, `decimals`?, `grouping`? | `string` | Formats a number as a currency string. |
| `formatDate` | `value`, `format` | `string` | Formats a timestamp into a string using a pattern. |
| `pluralize` | `value`, `zero`?, `one`?, `two`?, `few`?, `many`?, `other` | `string` | Returns a localized string based on the Common Locale Data Repository (CLDR) plural category of the count (zero, one, two, few, many, other). |
| `openUrl` | `url` | `void` | Opens the specified URL in a browser or handler. |
| `and` | `values` | `boolean` | Performs a logical AND operation on a list of boolean values. |
| `or` | `values` | `boolean` | Performs a logical OR operation on a list of boolean values. |
| `not` | `value` | `boolean` | Performs a logical NOT operation on a boolean value. |

Notes:

- `dateIsBefore` and `dateIsBeforeOrEqual` return `true` while either date is unset, so empty fields do
  not show range errors. Dates are `{"year", "month", "day"}` objects (month 1–12).
- `length` and `numeric` need at least one of `min` and `max`.
- `formatString` interpolates `${/absolute/path}`, `${relative/path}` and named-argument calls such as
  `${formatCurrency(value:${/total}, currency:'USD')}`. Escape a literal `${` as `\${`.
- `openUrl` is registered, but in Gemini Enterprise a Button or MaterialButton click always starts an
  agent turn, also for `functionCall` actions. For a link without a turn, use a markdown link in
  `MaterialText`, `MaterialCard.href` or a `GcbpTable` `LINK` cell.

## Validation with checks

Inputs that accept `checks` take a list of rules; a rule whose condition is `false` shows its message:

```json
{"id": "email", "component": "MaterialInput", "label": "Work email", "value": {"path": "/form/email"},
 "checks": [
   {"condition": {"call": "required", "args": {"value": {"path": "/form/email"}}, "returnType": "boolean"}, "message": "Email is required"},
   {"condition": {"call": "email", "args": {"value": {"path": "/form/email"}}, "returnType": "boolean"}, "message": "Enter a valid email address"}
 ]}
```

Disable a submit button until fields are valid:

```json
{"id": "submit", "component": "MaterialButton", "label": "Submit",
 "disabled": {"call": "not", "args": {"value": {"call": "areComponentsValid",
   "args": {"componentIds": ["email"]}, "returnType": "boolean"}}, "returnType": "boolean"},
 "action": {"event": {"name": "submit_request", "context": {"prompt": "Submit the request", "email": {"path": "/form/email"}}}}}
```

## Styling

- `style` is accepted by `Material*` components and `MosaicSlideCard` only. Basic components (`Text`, `Row`, `Column`, `Card`, `Button` and others) do not accept `style`.
- Keys are camelCase DOM style names; values are strings. Kebab-case keys and keys outside the
  allowlist fail validation.
- Positioning and layering properties are not in the allowlist (`position`, `top`, `left`, `right`,
  `bottom`, `inset`, `zIndex`, `opacity`, `transform`, `filter`, `pointerEvents`, `cursor`), to
  prevent content from covering the host interface.
- Gemini Enterprise applies its own Material 3 theme; `createSurface` has no theme or colour settings.
  CSS variables such as `--a2ui-color-primary` can be set through `style` where needed.

### Style allowlist (193 keys)

`accentColor`, `alignContent`, `alignItems`, `alignSelf`, `aspectRatio`, `background`, `backgroundAttachment`, `backgroundClip`, `backgroundColor`, `backgroundImage`, `backgroundOrigin`, `backgroundPosition`, `backgroundPositionX`, `backgroundPositionY`, `backgroundRepeat`, `backgroundSize`, `border`, `borderBlock`, `borderBlockColor`, `borderBlockEnd`, `borderBlockEndColor`, `borderBlockEndStyle`, `borderBlockEndWidth`, `borderBlockStart`, `borderBlockStartColor`, `borderBlockStartStyle`, `borderBlockStartWidth`, `borderBlockStyle`, `borderBlockWidth`, `borderBottom`, `borderBottomColor`, `borderBottomLeftRadius`, `borderBottomRightRadius`, `borderBottomStyle`, `borderBottomWidth`, `borderCollapse`, `borderColor`, `borderEndEndRadius`, `borderEndStartRadius`, `borderInline`, `borderInlineColor`, `borderInlineEnd`, `borderInlineEndColor`, `borderInlineEndStyle`, `borderInlineEndWidth`, `borderInlineStart`, `borderInlineStartColor`, `borderInlineStartStyle`, `borderInlineStartWidth`, `borderInlineStyle`, `borderInlineWidth`, `borderLeft`, `borderLeftColor`, `borderLeftStyle`, `borderLeftWidth`, `borderRadius`, `borderRight`, `borderRightColor`, `borderRightStyle`, `borderRightWidth`, `borderSpacing`, `borderStartEndRadius`, `borderStartStartRadius`, `borderStyle`, `borderTop`, `borderTopColor`, `borderTopLeftRadius`, `borderTopRightRadius`, `borderTopStyle`, `borderTopWidth`, `borderWidth`, `boxShadow`, `boxSizing`, `captionSide`, `caretColor`, `clear`, `color`, `colorScheme`, `columnCount`, `columnGap`, `columnRule`, `columnRuleColor`, `columnRuleStyle`, `columnRuleWidth`, `columnSpan`, `columnWidth`, `columns`, `direction`, `display`, `emptyCells`, `flex`, `flexBasis`, `flexDirection`, `flexFlow`, `flexGrow`, `flexShrink`, `flexWrap`, `float`, `font`, `fontFamily`, `fontSize`, `fontSizeAdjust`, `fontStretch`, `fontStyle`, `fontVariant`, `fontWeight`, `gap`, `grid`, `gridArea`, `gridAutoColumns`, `gridAutoFlow`, `gridAutoRows`, `gridColumn`, `gridColumnEnd`, `gridColumnStart`, `gridRow`, `gridRowEnd`, `gridRowStart`, `gridTemplate`, `gridTemplateAreas`, `gridTemplateColumns`, `gridTemplateRows`, `height`, `justifyContent`, `justifyItems`, `justifySelf`, `letterSpacing`, `lineHeight`, `listStyle`, `listStyleImage`, `listStylePosition`, `listStyleType`, `margin`, `marginBlock`, `marginBlockEnd`, `marginBlockStart`, `marginBottom`, `marginInline`, `marginInlineEnd`, `marginInlineStart`, `marginLeft`, `marginRight`, `marginTop`, `maxHeight`, `maxWidth`, `minHeight`, `minWidth`, `objectFit`, `objectPosition`, `order`, `outline`, `outlineColor`, `outlineOffset`, `outlineStyle`, `outlineWidth`, `overflow`, `overflowWrap`, `overflowX`, `overflowY`, `padding`, `paddingBlock`, `paddingBlockEnd`, `paddingBlockStart`, `paddingBottom`, `paddingInline`, `paddingInlineEnd`, `paddingInlineStart`, `paddingLeft`, `paddingRight`, `paddingTop`, `placeContent`, `placeItems`, `placeSelf`, `rowGap`, `tableLayout`, `textAlign`, `textDecoration`, `textDecorationColor`, `textDecorationLine`, `textDecorationStyle`, `textIndent`, `textOverflow`, `textShadow`, `textTransform`, `textUnderlineOffset`, `unicodeBidi`, `verticalAlign`, `visibility`, `whiteSpace`, `width`, `wordBreak`, `wordSpacing`, `wordWrap`
