# Theming a Canvas page: tokens, Tailwind v4 and Radix (Gemini Enterprise)

How to style a Pattern 3 page so that one set of design tokens drives Tailwind utilities, Radix components, SVG charts and
a light and a dark theme. The Trend Signals blueprint uses this with a Google Cloud look.

## Layers

1. **Tokens**: CSS custom properties on `:root` (primary ramp, surfaces, text, lines, status, on-accent, tooltip, shadow, fonts).
   `[data-theme="dark"]` redefines the same names. This is the only place a color value is written.
2. **Tailwind theme**: map semantic names onto the variables with `@theme inline`.
3. **Components**: Radix primitives for behavior and ARIA, Tailwind classes for appearance, including state through data attributes.
4. **Views**: built from the components. Colors that come from data are set inline.

## Tailwind v4 configuration

```css
@import "./tokens.css";
@import "tailwindcss";

@theme inline {
  --color-paper: var(--bg);  --color-card: var(--surface);
  --color-ink: var(--ink);   --color-ink3: var(--ink-3);   --color-line: var(--hairline);
  --color-accent: var(--blue-700);  --color-accent-soft: var(--blue-50);
  --color-good: var(--bullish);     --color-bad: var(--risk);
}
```

- `inline` makes utilities reference `var(--surface)` at runtime, so switching `data-theme` re-themes every utility without a rebuild.
- Use role names (`bg-card`, `text-ink3`, `border-line`, `bg-accent-soft`), not color names. Opacity syntax (`border-accent/40`) works.
- For one-offs use variables directly: `shadow-[var(--shadow)]`, `text-[var(--on-accent)]`, `fill-[var(--ws-tint)]`.
- Tailwind's output is in CSS layers; unlayered CSS beats it. Keep other CSS inside `@layer`, or do not write any.
- Join class names with `clsx` and `tailwind-merge` so callers can override a component's defaults.

## Radix with Tailwind

Radix is unstyled. Style states with its data attributes:

```tsx
<Tabs.Trigger className="text-ink3 data-[state=active]:text-ink after:h-[2px] data-[state=active]:after:bg-accent" />
<ToggleGroup.Item className="data-[state=on]:bg-accent data-[state=on]:text-[var(--on-accent)]" />
<Select.Item className="data-[highlighted]:bg-accent-soft" />
```

Menus, selects and tooltips render in a portal; inside an iframe the portal is the iframe's `body`, which is what you want.

## A Google Cloud look

- Primary: Google blue `#1a73e8` as `--blue-600`; text greys `#202124 / #3c4043 / #5f6368 / #80868b`; lines `#dadce0 / #e8eaed`;
  background `#f8f9fa` on `#ffffff` cards.
- Status: green `#1e8e3e`, red `#d93025`, amber `#f9ab00` (text `#b06000`). Show status with a label or an arrow, never color alone.
- Shape: pill buttons, chips and inputs; `rounded-xl` cards with a 1 px border and Material's two-layer shadow.
- Type: `"Google Sans", "Google Sans Text", Roboto, system-ui`; regular or medium weights. The frame has no network, so web fonts cannot
  be linked; use the installed font or inline one as a data URI.
- A four-color rule (blue, red, yellow, green) under the header.

## Dark theme

Redefine the tokens under `[data-theme="dark"]` (Google dark: `#202124` background, `#292a2d` surfaces, `#e8eaed` text). Re-map the
ramp so the roles hold: the accent used for text and primary buttons becomes the light blue `#8ab4f8`, the soft accent background a deep
blue, and `--on-accent` turns dark so button text keeps its contrast. Invert the tooltip. Gemini Enterprise does not pass its theme to
the frame, so ship a toggle that sets `document.documentElement.dataset.theme`.

## Data-driven color

- Category and series colors are set inline from the data, from a palette that works on both themes.
- A header tinted from an item's own color needs a luminance check to choose white or dark text.
- `color-mix(in srgb, var(--blue-600) N%, var(--surface))` gives a scale that follows the theme (heatmaps).
- SVG should use theme classes (`stroke-line2`, `fill-ink4`) and `var(--surface)` for halos and outlines.

## Rules

1. Semantic classes for surfaces, text and borders; a hex value is either data (inline) or a missing token.
2. Text on an accent background uses `--on-accent`, never `text-white`.
3. Check every view in both themes.
4. Use Radix for anything interactive.
5. No unlayered CSS.
6. Keep radii and shadows to a small set.
7. To restyle for another brand, change the tokens and the data palette; components stay the same.
