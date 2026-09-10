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
