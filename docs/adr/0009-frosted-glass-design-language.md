# Frosted-glass design language over the native CSS token layer

---
status: accepted
---

The Studio frontend adopts a frosted-glass ("glassmorphism") visual language:
translucent white chrome panes and floating cards blur a soft multi-hue
gradient canvas, implemented entirely as new tokens and values inside the
existing plain-CSS custom-property system in `frontend/src/styles/base.css`
(with the BEM-ish class contract unchanged). The editor pane keeps an opaque
writing surface. No CSS framework, component library, or new dependency is
introduced; root `DESIGN.md` (schema `@google/design.md`) is the design
source of truth and `base.css` is its executable mirror.

## Context

The owner asked for a thorough glassmorphism redesign that prefers mature
frameworks and component libraries and avoids reinventing wheels, while the
`ponytail` discipline demands the laziest solution that works. Three facts
decided the trade-off:

- The existing BEM-ish class names are a stable contract anchored by ~70
  Playwright class locators and 567 unit tests with zero visual assertions;
  migrating to Tailwind or shadcn/ui would rewrite all 1,531 lines of CSS,
  rename the contract, and touch every test file, for no behavioral gain.
- Glassmorphism is a native CSS platform feature (`backdrop-filter` is
  Baseline 2024); the mature wheels the product needs — React 19,
  CodeMirror 6, lucide-react, Fontsource — are already installed. The
  Linear redesign is the industry precedent for dense tool UIs shipping a
  visual overhaul through a token-variable system rather than a component
  library.
- AI-coding friendliness comes from an explicit, executable single source
  of truth plus stable contracts, not from a particular framework: a
  one-file token block mirrored by a machine-lintable DESIGN.md minimizes
  the surface an agent must read and the diff it must produce. Framework
  familiarity mainly helps generating new UI from scratch, not iterating
  on an existing anchored codebase.

Research constraints encoded into the tokens: glass only on chrome and
floating layers (never the editor, never children of a glass pane, never
sticky bars over scrolling content — Chromium nested-blur limitation and
scroll-time blur recomputation cost); blur capped at two tiers (14px/24px)
with literal values on the `-webkit-` fallback line (Safari does not accept
CSS variables there); `prefers-reduced-transparency: reduce` raises glass
alpha to near-opaque and disables blur via one token override block; an
`@supports` block falls back to solid surfaces where `backdrop-filter` is
unavailable; text contrast on translucent surfaces is verified against the
lightest and darkest gradient stops with a premultiplied approximation.

## Decision

Ship the glass redesign as values inside the existing token system: new
`base.css` tokens (`--canvas-gradient`, `--surface-glass{,-strong,-faint}`,
`--glass-blur{,-strong}`, `--glass-border`, `--glass-shadow`, canvas hint
tints), material-only changes to the nine feature CSS files (class names,
geometry, 44px targets, breakpoints, and all observable behavior frozen),
and a matching DESIGN.md v2 that passes `npx @google/design.md lint` /
`diff`. No OpenSpec change: the capability spec's 72 requirements are
behavioral contracts and constrain none of the visual properties being
changed. Dark mode is explicitly out of scope (the `@google/design.md`
alpha schema has no themes syntax yet) and remains a separate future task.
