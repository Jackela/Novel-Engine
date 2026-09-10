# Align row-level selected-state text with the teal token

Written against: 11b4e5ef

## Evidence chain

- Surface: Studio navigation tree (`frontend/src/styles/studio-nav.css`), document rows vs section buttons.
- Problem: the same selected-state presentation (teal text on `--teal-soft`) uses two different teals: `.studio-nav__section--active` uses `color: var(--teal-strong)` (studio-nav.css:109) while `.document-row--active` uses the literal `#0f6862` (studio-nav.css:379) — a direct contradiction between sibling selected-state treatments on the same surface.
- Design evidence: root `DESIGN.md` (Colors): teal reserved for "primary actions, selection, focus, and positive state" with tokens as the single source; `--teal-strong: #0f766e` (base.css:16).
- Owner: `frontend/src/styles/base.css` (`--teal-strong`).
- Scope and affected surfaces: studio-nav.css:379 (`.document-row--active` text), :410 (`.document-row--active .document-row__beat`); contrast-load-bearing exceptions at :395 and :432 (see decision).
- Uncertainty: none for the two switched lines — `--teal-strong` on `--teal-soft` measures ≈4.8:1 (WCAG AA pass for normal text, computed against sRGB luminance of #0f766e=0.140, #dff3f1=0.861).

## Design decision

Use `var(--teal-strong)` for selected-state row text whose background is `--teal-soft` (lines 379, 410), matching `.studio-nav__section--active`. Keep `#0f6862` at lines 395 and 432: those badge texts sit on `#cfe4e2`, where `--teal-strong` would measure ≈4.17:1 (AA fail for 11px text) while `#0f6862` measures ≈5.0:1 — the darker teal is load-bearing for contrast and stays, with a comment stating that constraint.

## Reuse

- `var(--teal-strong)` from `frontend/src/styles/base.css`
- Exemplar: `studio-nav.css:107-110` (`.studio-nav__section--active` — teal text on teal-soft).

## Changes

1. `frontend/src/styles/studio-nav.css:379`
   - Change: `color: #0f6862;` → `color: var(--teal-strong);`
   - Preserve: `background: var(--teal-soft)` unchanged.
   - Verify: active row text matches active section text color.
2. `frontend/src/styles/studio-nav.css:410`
   - Change: `color: #0f6862;` → `color: var(--teal-strong);`
   - Preserve: `.document-row--active` beat-visibility behavior.
   - Verify: beat suffix text on active rows is token teal.
3. `frontend/src/styles/studio-nav.css:395` and `:432`
   - Change: add one-line comment `/* darker teal: --teal-strong fails AA (4.17:1) on #cfe4e2 */`; value unchanged.
   - Preserve: exact `#0f6862` on `#cfe4e2`.
   - Verify: badge contrast unchanged (≈5.0:1).

## Scope

- Inherit: document-row selected state in the nav tree.
- Verify: studio nav rendering (active section vs active document row), lore stable badge, ordinal badge on active rows.
- Exclude: entry/library surfaces (no `#0f6862` there); any change to badge backgrounds.

## Validation

- Product: selecting a document row shows the same teal as selecting a nav section.
- Interface: studio nav at desktop and <950px collapsed layouts; rows with ordinal badges and lore stable badges.
- System: one teal token governs selected text except the documented badge exception.
- Repository: `pnpm --dir frontend lint && pnpm --dir frontend build` → clean; `pnpm --dir frontend test:unit` → pass.

## Stop conditions

- Stop if badge backgrounds (`#cfe4e2`, `#dff3f1`) have changed — contrast math must be recomputed first.

## Design documentation

- After acceptance and validation: none — DESIGN.md already fixes the semantic; the badge exception stays implementation-local (comment in place).
