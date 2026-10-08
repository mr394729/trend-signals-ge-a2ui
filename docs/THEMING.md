# Theming: Tailwind, tokens and Radix in a Google Cloud look

This document explains how the page is styled: where the colors come from, how Tailwind reads them, how the Radix
components are dressed, and how the light and dark themes switch. The rules at the end keep the system consistent when
views are added.

## The layers

```
tokens.css            custom properties: the only place a color or shadow value is written
   │  var(--…)
styles.css            @theme inline: gives Tailwind semantic names for those variables
   │  utility classes (bg-card, text-ink3, border-line, …)
components.tsx        Radix primitives + Tailwind utilities: Tabs, Segmented, Pick, Tip, Card, Btn, Tag, Bar, …
   │
scenes/…              views built from the components; data colors set inline from the data
```

A component never contains a hex color for a surface, text or border. It contains a semantic class, and the theme decides
the value.

## 1. Tokens (`frontend/src/lib/tokens.css`)

Everything is a CSS custom property on `:root`, and `[data-theme="dark"]` redefines the same names.

| Group | Names | Light value (Google Cloud) |
|---|---|---|
| Primary ramp | `--blue-50` … `--blue-900` | `#e8f0fe` … `#174ea6`; Google blue is `--blue-600` (`#1a73e8`) |
| Surfaces | `--bg`, `--surface`, `--surface-2` | `#f8f9fa`, `#ffffff`, `#f1f3f4` |
| Text | `--ink`, `--ink-2`, `--ink-3`, `--ink-4` | `#202124`, `#3c4043`, `#5f6368`, `#80868b` (the Material greys) |
| Lines | `--hairline`, `--hairline-2` | `#dadce0`, `#e8eaed` |
| Status | `--bullish*`, `--risk*`, `--escalated*`, `--neutral*` | Google green `#1e8e3e`, red `#d93025`, amber text `#b06000` |
| On-color | `--on-accent` | `#ffffff` (text on the primary color) |
| Tooltip | `--tip-bg`, `--tip-fg` | `#3c4043`, `#ffffff` |
| Quadrant tint | `--ws-tint` | `#e8f0fe` |
| Elevation | `--shadow` | Material's two-layer shadow `0 1px 2px … , 0 1px 3px 1px …` |
| Type | `--font`, `--serif` | `"Google Sans Text", "Google Sans", Roboto, system-ui, …` and `"Google Sans", "Google Sans Display", Roboto, …` |

`--serif` is a historical name: it holds the display font, which in this theme is the sans stack, so `font-serif`
classes render in Google Sans. Google Sans is used when it is installed; otherwise the stack falls back to Roboto or the
system font. The frame has no network, so web fonts cannot be linked; a font can only be used if it is inlined as a data
URI in the bundle.

The lifecycle and series colors are data colors, not theme colors. They are the Google palette (`LIFE_COLOR` in
`lib/trends.ts`: cyan `#12b5cb`, green `#1e8e3e`, blue `#1a73e8`, amber `#f9ab00`, grey `#9aa0a6`; the comparison series
use blue, red and green) and are applied inline from the data.

### Dark theme

`[data-theme="dark"]` follows Google's dark palette: `#202124` background, `#292a2d` surfaces, `#e8eaed` text,
`#3c4043` lines. The blue ramp is re-mapped so that the semantic roles still read correctly: `--blue-700`, the accent used
for text, links, active tabs and the primary button, becomes the light blue `#8ab4f8`, and `--blue-50`, the soft accent
background, becomes a deep blue `#1c2b44`. Because the accent is now light, `--on-accent` becomes dark (`#202124`) so
button text keeps its contrast. The tooltip inverts (`--tip-bg` light, `--tip-fg` dark).

Gemini Enterprise does not pass its theme to the frame, so the page has its own toggle. `TrendsScene` sets
`document.documentElement.dataset.theme` from a state value; nothing else changes, because every component reads tokens.

## 2. Tailwind v4 (`frontend/src/styles.css`)

```css
@import "./lib/tokens.css";
@import "tailwindcss";

@theme inline {
  --color-paper: var(--bg);        --color-card: var(--surface);
  --color-ink: var(--ink);         --color-ink2: var(--ink-2);   --color-ink3: var(--ink-3);   --color-ink4: var(--ink-4);
  --color-line: var(--hairline);   --color-line2: var(--hairline-2);
  --color-accent: var(--blue-700); --color-accent-soft: var(--blue-50);
  --color-good: var(--bullish);    --color-bad: var(--risk);     --color-warn: #c27a1a;
  --font-serif: var(--serif);
}
```

* **Semantic names.** `bg-card`, `bg-paper`, `text-ink3`, `border-line`, `bg-accent-soft`, `text-good`, `text-bad`. The names say
  the role, not the color.
* **`inline` matters.** `@theme inline` makes the generated utilities reference `var(--surface)` at runtime instead of copying
  its value when the CSS is built. That is what lets `[data-theme="dark"]` change every utility without a second build.
* **Opacity.** Tailwind's `/` opacity syntax works on these names (`border-accent/40`, `bg-accent-soft/60`) through
  `color-mix`, in both themes.
* **Arbitrary values.** Anything not worth a name uses a variable directly: `shadow-[var(--shadow)]`, `text-[var(--on-accent)]`,
  `fill-[var(--ws-tint)]`.
* **Layers.** `@import "tailwindcss"` places theme, base and utilities in CSS layers. Unlayered CSS beats layered CSS, so the
  page has almost none: two base rules (`button { cursor: pointer }`, the focus ring) inside `@layer base`, the highlight ring
  animation, and the reduced-motion rule. Do not add unlayered element rules; they would silently override utilities.
* **Preflight is on.** The page starts from Tailwind's reset and a 14 px base size.
* **`cn()`** (`lib/cn.ts`) joins class names with `clsx` and resolves conflicts with `tailwind-merge`, so a component's defaults
  can be overridden by its caller.

## 3. Components: Radix behavior, Tailwind appearance (`frontend/src/components.tsx`)

Radix primitives are unstyled: they provide the keyboard handling, focus management and ARIA. The classes provide the look,
including the state, through Radix's data attributes:

```tsx
<Tabs.Trigger className="… text-ink3 hover:text-ink data-[state=active]:text-ink
                          after:absolute after:inset-x-0 after:-bottom-px after:h-[2px]
                          data-[state=active]:after:bg-accent" />
<ToggleGroup.Item className="rounded-full px-3.5 py-1 text-ink3 data-[state=on]:bg-accent
                             data-[state=on]:text-[var(--on-accent)]" />
<Select.Item className="… data-[highlighted]:bg-accent-soft data-[highlighted]:text-ink" />
```

The Google Cloud conventions in the kit:

| Element | Treatment |
|---|---|
| Buttons, segmented controls, select triggers, search field, chips | Pills (`rounded-full`); primary is filled with the accent, secondary is outlined |
| Cards, tables, the map panel | `rounded-xl`, 1 px `border-line`, the Material shadow |
| Poster header, swatch tiles | `rounded-2xl` / `rounded-xl` |
| Tabs | Text tabs with a 2 px accent underline on the active one; 14.5 px, medium weight |
| Headings | Google Sans at regular or medium weight with slightly tight tracking; no italics, no serif |
| Brand mark | A 3 px four-color rule (blue, red, yellow, green) under the masthead |
| Status | Green, red and amber from the tokens, always with a label or an arrow, never color alone |
| Menus and tooltips | Radix portals; `rounded-xl` panel with border and shadow; tooltip uses `--tip-bg` / `--tip-fg` |

`Card`, `CardTitle`, `Btn`, `Tag`, `LifePill`, `Momentum` and `Bar` are small wrappers over those classes; views use them
instead of repeating class strings.

## 4. Data-driven color

Some color comes from the data and cannot be a token:

* **Lifecycle and series colors** are set inline (`style={{ color: LIFE_COLOR[t.life] }}`, SVG `fill`).
* **The poster** is tinted from the trend's lead swatch: `linear-gradient(118deg, lead 0%, lead 52%, support 135%)`, with white or
  dark text chosen by relative luminance (`luminance()` in `Views.tsx`), and an SVG fabric texture in `currentColor` over it.
* **The heatmap** mixes the primary into the surface by value: `color-mix(in srgb, var(--blue-600) N%, var(--surface))`, so it follows
  the theme.
* **SVG** uses theme classes (`stroke-line2`, `fill-ink4`, `fill-accent-soft`) and `var(--surface)` for halos and bubble outlines,
  so charts re-theme with the page.

## 5. Adding a view: rules

1. Use semantic classes for surfaces, text and borders. If you reach for a hex value, ask whether it is data (inline) or a missing
   token (add it to `tokens.css` for both themes and, if Tailwind needs it, to `@theme inline`).
2. Text on an accent background uses `--on-accent`; never `text-white`.
3. Anything that can be light on dark needs checking in both themes: render both (`make screenshots` renders the dark theme too).
4. Prefer the kit (`Card`, `Btn`, `Pick`, …) and Radix primitives for anything interactive.
5. Do not add unlayered CSS. Use utilities, or put the rule in `@layer base` / `@layer components`.
6. Keep radii and shadows to the set above so the surfaces read as one system.
7. Status colors always come with text or an icon.

## 6. Changing the look

The theme is a token swap. To restyle (another brand, another cloud's palette): change `tokens.css` (the blue ramp, greys, status
colors, fonts, shadow), the lifecycle palette in `lib/trends.ts`, and the four-color rule in `TrendsScene.tsx`. No component changes.
