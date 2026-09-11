# Dark mode: system-following dual-theme rendering

## Why

The Studio renders a single light theme. This is a recorded, deliberate
limitation (ADR-0009: "Dark mode is explicitly out of scope; the
`@google/design.md` alpha schema has no themes syntax yet and remains a
separate future task"), not an oversight — but it is a real product gap.
Novel Engine is a self-hosted writing studio whose core loop is long-form
drafting, frequently at night. A light-only canvas forces every night-time
session onto a bright surface, and the frosted-glass token layer shipped by
ADR-0009 already isolates every painted surface behind `base.css` custom
properties, so the marginal cost of a second theme is now token values plus
selection plumbing rather than a rewrite.

## What Changes

- Add a three-state theme selection — `system` (default), `light`, `dark` —
  exposed in the product UI. `system` follows `prefers-color-scheme`,
  including live OS preference changes while the app is open.
- A manual selection persists to `localStorage` under the key
  `novel_engine_theme` (values `system` / `light` / `dark`) and overrides the
  OS preference; an explicit `light` lock renders light even when the OS
  prefers dark, and vice versa. Missing, invalid, or unreadable storage
  degrades silently to `system` behavior.
- Dark rendering is an elevated-dark variant of the existing design language:
  layered cool-gray surfaces that lighten with elevation, dark variants of
  the three canvas hint tints and their radial color fields, a brightened
  teal accent with dark text-on-accent, and `color-scheme: dark` for native
  controls and scrollbars. Glass stays on chrome and floating layers only;
  the manuscript editor keeps an opaque (now dark) surface per ADR-0009.
- The dual theme is expressed as a second value set for the existing
  `:root` custom-property tokens in `frontend/src/styles/base.css`. All
  surfaces that consume tokens — entry page, project library, studio
  chrome, editor, inspector, usage panels — follow the active theme
  automatically with no per-surface theme logic.
- The two documented raw-color exceptions from the glass campaign (the
  studio-nav badge family and the `.library__project-row:hover` `#8dbab6`)
  are folded into named tokens so no painted surface is left light-only.
- No first-paint theme flash: a blocking inline script in `index.html`
  applies a stored manual selection before the first frame; the `system`
  path needs no script at all (pure CSS media-query fallback).
- `prefers-reduced-transparency: reduce` and no-`backdrop-filter` fallbacks
  gain dark variants so the existing fallback chain stays intact in both
  themes.
- Root `DESIGN.md` gains a documented representation for the dark values
  (body appendix table; frontmatter schema untouched — see design.md) and is
  regenerated deliberately through the `@google/design.md` lint/diff gates.

## Impact

- No breaking change: no API, OpenAPI, database, migration, server, or
  dependency surface is touched. The change is frontend CSS, `index.html`,
  new theme-selection UI, and documentation.
- New client storage: `localStorage` key `novel_engine_theme`. No cookie, no
  server-side preference, no cross-device sync.
- Affected surfaces: every frontend surface at once (entry, library,
  studio), because all of them already consume the shared token layer.
- Spec: one added requirement ("Theme selection and dual-theme rendering")
  in the `novel-engine` capability; existing requirements are unaffected —
  the capability spec's 72 requirements are behavioral contracts that
  constrain none of the visual properties (ADR-0009 finding, still true).
- E2E surface: one new Playwright theme workflow (select, persist, reload,
  OS-emulation matrix) alongside the existing `frontend/tests/e2e-ts/`
  specs.
- Gates touched: `@google/design.md` lint/diff (deliberate regeneration),
  frontend unit suite (new token drift-guard and contrast tests), existing
  visual-language documentation (`DESIGN.md` body, ADR-0009 relationship
  recorded in ADR-0010).
