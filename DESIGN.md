---
version: alpha
name: Novel Engine
description: Self-hosted writing studio — restrained neutral canvas, teal semantic accent, IBM Plex Sans product type over a serif writing surface.
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
  surface-muted: "#fafbfb"
  surface-panel: "#fcfcfc"
  surface-hover: "#f4f5f5"
  line-strong: "#bfc5c6"
  line: "#dfe2e3"
  muted: "#4b5556"
  muted-soft: "#626a6b"
  muted-faint: "#697172"
  teal-soft: "#dff3f1"
  teal-strong: "#0f766e"
  teal-hover: "#115e59"
  focus-ring: "#ccfbf1"
  danger: "#b91c1c"
  danger-soft: "#fff1f2"
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
    backgroundColor: "{colors.surface}"
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
    backgroundColor: "{colors.surface}"
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

The interface is a restrained, high-contrast neutral canvas with teal as the
single semantic accent. Dense panels, compact controls, and standard tabs are
intentional: the UI serves an active writing workflow, so consistency and
task visibility take priority over decorative surfaces.

## Colors

- Neutral surfaces carry the interface; teal is reserved for semantic
  meaning — primary actions, selection, focus, and positive state.
- Shared CSS custom-property tokens are defined once in the `:root` block of
  `frontend/src/styles/base.css`; components reuse those tokens instead of
  introducing one-off colors.
- Destructive and error states use the `danger` / `danger-soft` pair;
  `muted` tones are for secondary text, never for interactive accents.

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
- Interactive controls share a uniform minimum target height (see the
  `button` and `input` components) so dense panels stay operable.
- Below the compact breakpoint the panes collapse into a single scrolling
  column ordered editor-first.

## Shapes

- Surfaces are separated by hairline borders, not drop shadows; the focus
  ring is the only halo in the interface.
- Controls use small radii; cards and panels sit slightly rounder than
  controls.

## Components

- Cross-feature primitives use the `ui-` block prefix (`ui-command`,
  `ui-form-error`, `ui-spin`, `ui-brand`) and live in
  `frontend/src/styles/base.css`; feature styles use feature-prefixed
  BEM-ish blocks (`block__element--modifier`).
- Buttons are `ui-command` with `--primary` and `--icon` modifiers; focus is
  always visible — a solid teal outline for buttons and menus, a teal border
  plus `focus-ring` halo for text inputs.
- Icons inherit the shared svg defaults (uniform small size, narrow stroke)
  and align to the adjacent text size.

## Do's and Don'ts

- Do preserve visible focus, disabled, loading, error, and selected states
  on interactive controls.
- Do keep motion limited to state feedback and respect
  `prefers-reduced-motion: reduce`.
- Don't introduce one-off colors — reuse the tokens in
  `frontend/src/styles/base.css`.
- Don't add decorative motion or animated surfaces beyond state feedback.
