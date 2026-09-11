---
version: alpha
name: Novel Engine
description: Self-hosted writing studio — frosted daylight glass. Translucent white chrome and floating cards blur a soft multi-hue gradient canvas; the editor keeps a calm opaque serif writing page; teal remains the single semantic accent.
omitted:
  - section: spacing
    reason: "No named spacing token scale; spacing values are per-component in frontend/src/styles/"
  - section: rounded
    reason: "No named radius token; radii are component contracts (see components)"
colors:
  ink: "#18181b"
  ink-soft: "#27272a"
  surface: "#ffffff"
  canvas: "#f7f8f8"
  canvas-hint-teal: "#d9eee9"
  canvas-hint-blue: "#d7e3f7"
  canvas-hint-violet: "#e8def5"
  surface-glass: "rgba(255, 255, 255, 0.62)"
  surface-glass-strong: "rgba(255, 255, 255, 0.80)"
  surface-glass-faint: "rgba(255, 255, 255, 0.45)"
  surface-muted: "#fafbfb"
  surface-panel: "#fcfcfc"
  surface-hover: "#f4f5f5"
  line-strong: "#bfc5c6"
  line: "#dfe2e3"
  glass-border: "rgba(255, 255, 255, 0.65)"
  muted: "#4b5556"
  muted-soft: "#626a6b"
  muted-faint: "#697172"
  teal-soft: "#dff3f1"
  teal-strong: "#0f766e"
  teal-hover: "#115e59"
  focus-ring: "#ccfbf1"
  danger: "#b91c1c"
  danger-soft: "#fff1f2"
  danger-line: "#fecaca"
  warn: "#d8a62a"
  warn-soft: "#fdf6e3"
  warn-ink: "#6b5410"
  on-accent: "#ffffff"
typography:
  sans:
    fontFamily: "IBM Plex Sans Variable, system-ui, sans-serif"
  serif:
    fontFamily: "ui-serif, Georgia, Cambria, 'Times New Roman', Times, serif"
  mono:
    fontFamily: "ui-monospace, monospace"
  ui:
    fontFamily: "IBM Plex Sans Variable, system-ui, sans-serif"
    fontSize: 13px
    fontWeight: 600
components:
  button:
    backgroundColor: "{colors.surface-glass-strong}"
    textColor: "{colors.ink-soft}"
    typography: "{typography.ui}"
    rounded: 6px
    height: 44px
  button-primary:
    backgroundColor: "{colors.teal-strong}"
    textColor: "{colors.on-accent}"
    typography: "{typography.ui}"
    rounded: 6px
    height: 44px
  button-primary-hover:
    backgroundColor: "{colors.teal-hover}"
  button-icon:
    backgroundColor: "{colors.surface-glass-strong}"
    textColor: "{colors.ink-soft}"
    rounded: 6px
    height: 44px
    width: 44px
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: 5px
    height: 44px
---

# Novel Engine Design Notes

## Overview

Novel Engine is a self-hosted writing studio for drafting long-form fiction:
a project library leading into a three-pane workspace (navigation, editor,
inspector) for chapters, outlines, lore, reviews, and generated proposals.

The visual language is frosted daylight glass: chrome panes and floating
cards are translucent white surfaces that blur a soft multi-hue gradient
canvas, while the editor keeps a calm, opaque serif writing page. Teal
remains the single semantic accent. Dense panels, compact controls, and
standard tabs are intentional: the UI serves an active writing workflow, so
consistency and task visibility take priority over decorative surfaces.

## Colors

- The canvas is a soft diagonal gradient blending the three hint tints
  (teal, blue, violet) over `canvas`; glass surfaces frost whatever sits
  behind them. Glass comes in three elevation tiers: `surface-glass-faint`
  for ambient chrome, `surface-glass` for pane chrome, and
  `surface-glass-strong` for floating cards and controls.
- Teal is reserved for semantic meaning — primary actions, selection,
  focus, and positive state. Destructive and error states use the
  `danger` / `danger-soft` pair; `muted` tones are for secondary text,
  never for interactive accents.
- Shared CSS custom-property tokens are defined once in the `:root` block
  of `frontend/src/styles/base.css`; components reuse those tokens instead
  of introducing one-off colors. The gradient and glass alpha/blur tokens
  live there too, so the entire material system is tunable from one block.
- Text on glass must hold AA against the worst-case backdrop: verify
  contrast over both the lightest and the darkest gradient stop using a
  premultiplied approximation before shipping a new text/background pair.

## Typography

- Product UI uses self-hosted IBM Plex Sans Variable through Fontsource.
  `system-ui` is the fallback for environments that cannot load the bundled
  font.
- The writing surface intentionally uses the `ui-serif` stack for long-form
  reading and editing. This contrast is part of the product's
  writing-studio identity.
- Grouped metadata uses small uppercase micro-labels with slight letter
  spacing; generated-proposal previews use the `mono` stack.

## Layout

- The studio is a fixed three-pane grid (navigation, editor, inspector)
  between a top bar and a status bar; the inspector hosts stacked tab
  panels and the editor column keeps a measure suited to long-form reading
  (centered, capped width).
- The editor pane is the exception to glass: it renders an opaque
  `surface` page so keystroke and scroll performance and long-form
  readability never depend on blur recomputation.
- Interactive controls share a uniform minimum target height (see the
  `button` and `input` components) so dense panels stay operable.
- Below the compact breakpoint the panes collapse into a single scrolling
  column ordered editor-first.

## Shapes

- Glass surfaces carry a 1px light border (`glass-border`) and a soft,
  wide shadow (`glass-shadow` token in `base.css`); blur strength is two
  tiers — 14px for pane chrome, 24px for floating cards — and never more.
- Controls use small radii; floating cards sit rounder than controls.
- Surfaces inside a glass pane never apply their own `backdrop-filter`:
  one glass layer per stacking region (a Chromium limitation and a
  performance rule). Sticky bars over scrolling content use translucent
  fills without blur.

## Components

- Cross-feature primitives use the `ui-` block prefix (`ui-command`,
  `ui-form-error`, `ui-spin`, `ui-brand`) and live in
  `frontend/src/styles/base.css`; feature styles use feature-prefixed
  BEM-ish blocks (`block__element--modifier`).
- Buttons are `ui-command` with `--primary` and `--icon` modifiers; their
  translucent fill carries no blur of its own — the pane behind provides
  the frost. Focus is always visible — a solid teal outline for buttons
  and menus, a teal border plus `focus-ring` halo for text inputs.
- Icons inherit the shared svg defaults (uniform small size, narrow
  stroke) and align to the adjacent text size.

## Do's and Don'ts

- Do preserve visible focus, disabled, loading, error, and selected states
  on interactive controls.
- Do keep motion limited to state feedback and respect
  `prefers-reduced-motion: reduce`.
- Do honor `prefers-reduced-transparency: reduce` — the token block in
  `base.css` raises glass alpha to near-opaque and disables blur in one
  place; browsers without `backdrop-filter` fall back to solid surfaces
  via the `@supports` block.
- Don't introduce one-off colors — reuse the tokens in
  `frontend/src/styles/base.css`.
- Don't apply `backdrop-filter` to the editor surface, to children of a
  glass pane, or to sticky bars over scrolling content.
- Don't add decorative motion or animated surfaces beyond state feedback.

## Dark theme values

The product ships a second (dark) value set for the same tokens, per
ADR-0010. The frontmatter above keeps the canonical light values (the
`@google/design.md` alpha schema has no themes syntax); this appendix is the
dark representation. Dark values live once per selector entry in
`frontend/src/styles/base.css` and are mirrored here.

### Selection contract

- `<html>` carries `data-theme="dark"` or `data-theme="light"` only when an
  explicit lock is stored; with no attribute the OS preference decides
  through a pure-CSS `prefers-color-scheme` media entry — no JavaScript.
- Dark values are declared in two selector contexts, kept literally equal by
  a drift-guard unit test:
  `[data-theme="dark"]` and
  `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) }`.
- The user preference is tri-state (`system` / `light` / `dark`), persisted
  in `localStorage` under `novel_engine_theme`; absent, invalid, or
  unreadable storage always degrades silently to `system`.
- A blocking inline script in `index.html` applies a stored lock to
  `<html>` before the first painted frame (no flash); `system` does nothing.
- `:root` declares `color-scheme: light`; both dark entries declare
  `color-scheme: dark`, so native controls and scrollbars follow the theme.
- The reduced-transparency and no-`backdrop-filter` fallback blocks each
  carry dark twins (near-opaque dark fills, blur 0, solid borders, no
  shadow), so the material fallback chain holds in both themes.

### Dark token table

| Token | Dark value | Notes |
|---|---|---|
| `ink` | `#e6eaeb` | Primary text; 12.2:1 on worst-case glass, 14.6:1 on the opaque editor |
| `ink-soft` | `#c7ced0` | Strong secondary text, control labels (9.3:1) |
| `surface` | `#15191a` | Opaque editor page, inputs |
| `canvas` | `#101415` | Gradient base |
| `canvas-hint-teal` | `#122b28` | Gradient stop 0/100% |
| `canvas-hint-blue` | `#16232f` | Gradient stop 38% |
| `canvas-hint-violet` | `#1e1a2e` | Gradient stop 68% |
| `surface-glass` | `rgba(16, 20, 21, 0.62)` | Pane chrome frost; light alpha tiers unchanged |
| `surface-glass-strong` | `rgba(22, 27, 28, 0.80)` | Floating cards, controls |
| `surface-glass-faint` | `rgba(12, 16, 17, 0.45)` | Ambient chrome |
| `surface-muted` | `#171c1d` | Subdued fills |
| `surface-panel` | `#1a1f21` | Panel/card composite base |
| `surface-hover` | `#252c2e` | Hover elevation |
| `line-strong` | `#475355` | Strong hairlines |
| `line` | `#2f383a` | Hairlines |
| `glass-border` | `rgba(255, 255, 255, 0.14)` | Hairline highlight on dark glass |
| `glass-shadow` | `0 8px 32px rgba(0, 0, 0, 0.45)` | Deeper shadow; non-text decoration |
| `muted` | `#aeb9bb` | Secondary text, strongest tier (7.4:1) |
| `muted-soft` | `#a2adb0` | Tertiary text (6.4:1) |
| `muted-faint` | `#97a3a5` | Faint text, timestamps — floor pair, ≥5.5:1 target |
| `teal-soft` | `#11312d` | Soft selected/active wash |
| `teal-strong` | `#2dd4bf` | Accent: actions, selection, focus (7.9:1 on glass) |
| `teal-hover` | `#5eead4` | Primary hover lightens (dark convention) |
| `focus-ring` | `#113b36` | Focus halo, CM selection bg |
| `danger` | `#f08c8c` | Error text/icons (6.2:1 on glass, 6.9:1 on `danger-soft`) |
| `danger-soft` | `#381415` | Error wash |
| `danger-line` | `#6f2c2e` | Error borders |
| `warn` | `#e3b041` | Warning text/icons (7.4:1 on glass) |
| `warn-soft` | `#322712` | Warning wash |
| `warn-ink` | `#eed9a3` | Warning text on wash (10.5:1) |
| `on-accent` | `#0b2f2a` | Dark teal ink on the brightened accent fill (7.7:1) |

Dark `--canvas-gradient`: bright-source-over-dark radials —
`rgba(45, 212, 191, 0.09)` teal top-left and `rgba(139, 122, 235, 0.09)`
violet bottom-right — over the same hint-tint linear ramp. All text pairs
hold AA 4.5:1 against the worst-case glass composite (unit-tested from
`base.css`; floor pair `muted-faint` ≥5.5:1).

Supplementary badge/row-hover tokens (declared alongside the table above in
`base.css`; dark pairs unit-tested ≥4.5:1):

| Token | Dark value | Notes |
|---|---|---|
| `badge-neutral-bg` / `badge-neutral-ink` | `#252c2e` / `#aeb9bb` | 7.07:1 |
| `badge-active-bg` / `badge-active-ink` | `#11312d` / `#2dd4bf` | 7.52:1 |
| `badge-deprecated-bg` / `badge-deprecated-ink` | `#381415` / `#f08c8c` | Danger-family pair, 6.91:1 |
| `badge-draft-active-bg` / `badge-draft-active-ink` | `#2f383a` / `#c7ced0` | Active-row draft badge, 7.53:1 |
| `library-row-hover` | `#3d7a73` | Row hover wash |

Theme-invariant material tokens (`glass-blur` 14px, `glass-blur-strong`
24px) stay in `:root` only — blur strength does not change with the theme.
