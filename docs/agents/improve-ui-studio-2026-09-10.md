# improve-ui Studio audit — 2026-09-10

First production run of the `improve-ui` skill against Novel-Engine, executed
by the main agent (Owner delegated in-session implementation per the approved
plan). Audit followed improve-ui discipline: read-only product source, plans
written to `design-plans/`, implementation performed afterward by the main
agent against those plans.

## Design language (audit record)

- Audited surface: Studio three-pane workspace (studio-nav / editor /
  inspector) plus shared chrome (statusbar, usage panel) and, for
  exact-duplicate scope, entry/library surfaces.
- Design sources: root `DESIGN.md` (schema format, commit 08503395),
  `frontend/src/styles/base.css` (`:root` tokens), `frontend/src/index.css`
  conventions.
- Documented decisions: token reuse over one-off colors; teal reserved for
  primary/selection/focus/positive; hairline borders; states completeness.
- Governing owners: `base.css` tokens + `ui-` primitives; feature CSS files.
- Explicit exceptions: none documented.

## Findings (all three survived the vet pass)

| # | Problem | Evidence | Proposed change | Scope | Confidence |
|---|---|---|---|---|---|
| 1 | Hairline borders use literal `#dfe2e3` (exact `--line`) | 20 sites across 6 feature CSS files; `var(--line)` already used in same files (e.g. studio-nav.css:54) | Replace with `var(--line)` | 20 lines | high |
| 2 | Muted text uses exact token duplicates `#626a6b`/`#697172` | editor/entry/library/inspector vs `--muted-soft`/`--muted-faint` | Replace with tokens | 7 lines | high |
| 3 | Two teals for selected-state text on identical context | `.studio-nav__section--active` uses `var(--teal-strong)`; `.document-row--active` uses `#0f6862` | Align row/beat text to `var(--teal-strong)`; keep badge exceptions for AA contrast | 4 lines | medium |

Rejected candidates (near-match literals `#4f595a`, `#6f7778`, `#e1e4e5`,
`#636b6c` etc.): no exact token owner; correction would require choosing a
"nearest" token — invents intent, fails the correction proof.

Key vet result: switching the ordinal/lore-stable badge text
(`#0f6862` on `#cfe4e2`) to `--teal-strong` measures ≈4.17:1 — below AA 4.5
for 11px text — while `#0f6862` measures ≈5.0:1. Those two sites keep the
darker teal with an in-file comment stating the constraint.

## Plans and implementation

- `design-plans/2026-09-10-exact-token-duplicates.md` (findings 1+2) —
  27 literal→token replacements across 8 files, value-identical by
  definition.
- `design-plans/2026-09-10-selected-state-teal.md` (finding 3) — 2 sites
  switched to `var(--teal-strong)`, 2 badge sites kept with contrast
  comments.

Both implemented on top of `11b4e5ef`.

## Validation actually run

- `grep '#dfe2e3\|#626a6b\|#697172' frontend/src/styles/*.css` → only the
  three `base.css` token definitions remain; `#0f6862` remains exactly at
  the two commented badge sites.
- `pnpm --dir frontend lint` / `format:check` / `type-check` — clean;
  `test:unit` 567/567; `build` verified 0.6.0.
- Browser (main-session Playwright, dev server :5199): computed styles —
  `.document-row--active` and beat = `rgb(15, 118, 110)` (teal-strong),
  identical to `.studio-nav__section--active`; lore-stable badge stays
  `rgb(15, 104, 98)`.
- `pnpm --dir server gates` — all six clean (hygiene accepts
  `design-plans/`); `pnpm spec:validate` — 2 passed.

## Skips

- No OpenSpec change: token-equal substitution plus restoring documented
  design intent; no capability change.
- Near-match consolidation (e.g. `#4f595a` family) left as potential future
  work; requires an explicit design decision to merge or tokenize.
