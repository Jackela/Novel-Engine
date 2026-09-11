# Dual-theme token architecture: light `:root` baseline plus `data-theme` dark entries

---
status: accepted
---

The Studio frontend renders both a light and a dark theme from the same
plain-CSS custom-property system in `frontend/src/styles/base.css`. Light
values remain the `:root` baseline; dark values are a second value set
selected by a `data-theme` attribute on `<html>` combined with a pure-CSS
`prefers-color-scheme` media entry, so the default `system` mode needs no
JavaScript. Theme choice is a three-state preference
(`system`/`light`/`dark`) persisted in `localStorage` under
`novel_engine_theme`. This record extends, and does not amend, ADR-0009:
glass stays on chrome and floating layers only, the manuscript editor keeps
an opaque surface, and `base.css` stays the single home of raw color.

## Context

ADR-0009 shipped the frosted-glass language as values inside the existing
`:root` token block and explicitly deferred dark mode, because the
`@google/design.md` alpha schema has no themes syntax. The deferral left
three tensions that dark mode now has to resolve:

- Every painted surface already consumes `base.css` tokens, so a second
  theme is primarily a value problem — but selection, persistence, and
  first-paint correctness are behavior problems that tokens alone cannot
  express.
- The glass campaign's fallback chain
  (`prefers-reduced-transparency`, `@supports not (backdrop-filter…)`) and
  its contrast discipline (premultiplied worst-case approximation, AA
  floor, ≥5.5:1 aspirational target) are light-theme facts that must hold
  in dark, not be replaced by it.
- The repo's discipline is one auditable token SSOT mirrored by a
  machine-lintable DESIGN.md; any dark representation that splits or
  duplicates that SSOT across files, build steps, or frameworks would
  forfeit the property that made the glass redesign cheap to execute.

## Decision

1. **Token layering.** Light tokens stay in `:root`, unchanged. Dark tokens
   are declared in two selector contexts — `[data-theme="dark"]` and
   `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) }`
   — so an explicit light lock suppresses OS-following, a dark lock forces
   dark, and no attribute means the OS decides with zero script
   involvement. CSS has no token mixing, so the dark set is a duplicated
   literal block; equality between the duplicates (including the dark
   fallback twins inside both conditional override blocks) is enforced by a
   frontend drift-guard unit test, keeping the SSOT machine-checked.
2. **FOUC prevention.** A minimal total inline script in `index.html`
   applies a stored `light`/`dark` lock to `documentElement.dataset.theme`
   before the first frame; for `system`, absent, invalid, or unreadable
   storage it does nothing and CSS resolves the theme. The accepted cost:
   `index.html` gains a blocking inline script, so any future strict CSP
   must carry its hash.
3. **Selection state.** One small theme module owns the tri-state
   preference: read/write of the `novel_engine_theme` localStorage key
   (values exactly `system`/`light`/`dark`), silent degradation to
   `system` on any storage error, a `matchMedia` listener that re-applies
   `data-theme` only while unlocked, and a `theme-color` meta override for
   locks. Two `theme-color` metas with `media` attributes let the
   OS-following path stay script-free. No cookie, no server-side
   preference.
4. **`color-scheme`.** `:root` declares `color-scheme: light`; dark entries
   declare `color-scheme: dark`, so native controls and scrollbars follow
   the theme without per-widget rules.
5. **Dark value derivation.** Elevated dark: the neutral ramp lightens with
   elevation (canvas < surface-muted < surface < panel < hover), text
   tokens invert to a cool light ramp, the hint-tint family becomes deep
   desaturated fields with low-alpha bright radial glows, and the teal
   accent brightens with `on-accent` flipped to dark teal ink. Contrast is
   locked by a unit test that computes WCAG ratios from `base.css`: every
   text pair ≥4.5:1 against its worst-case glass composite, floor pair
   (`muted-faint`) ≥5.5:1, preserving the glass campaign's verification
   standard in executable form.
6. **DESIGN.md representation.** The alpha schema has no themes syntax, so
   the frontmatter keeps the canonical (light) value per token and dark
   values land as a `## Dark theme values` body appendix. `npx
   @google/design.md lint` keeps passing on the unchanged frontmatter;
   `npx @google/design.md diff` gates the additive update deliberately.
   A frontmatter dual-value syntax was rejected as an unvalidated schema
   extension.

## Consequences

- ADR-0009's material rules are strengthened, not relaxed: dark fills keep
  the same alpha tiers and blur caps, the editor stays opaque, one glass
  layer per stacking region, and the reduced-transparency /
  no-`backdrop-filter` fallback chain now holds in both themes.
- The "raw colors only in `base.css`" discipline becomes fully true: the
  two recorded light-theme exceptions (the `studio-nav.css` badge family
  and the `library.css` row-hover literal) are folded into tokens with
  dark variants instead of being duplicated per theme.
- Theme correctness no longer depends on JavaScript in the default path;
  the residual JS dependencies (lock application before first paint, live
  OS-follow re-resolution while locked-free, `theme-color` override) are
  small, testable, and degrade silently.
- Duplicated dark blocks are a permanent, guarded cost: removing the
  duplication would require a build step or the always-resolve-in-JS
  pattern, both rejected here; the drift-guard test is the standing
  payment.
- `DESIGN.md`'s dark appendix is documentation the schema cannot lint
  semantically; the executable mirror of those values is `base.css` plus
  the drift-guard and contrast tests, which is where drift will actually
  be caught.
- Dark mode is in scope for the capability specification as one added
  requirement (theme selection and dual-theme rendering); ADR-0009's note
  that the 72 behavioral requirements constrain no visual property remains
  true, and this ADR picks up the "separate future task" that record
  deferred.

## Implementation results

Accepted and shipped with the 2026-09-11 dark-mode campaign
(`openspec/changes/2026-09-11-dark-mode/`, issue #509):

- The dual entry landed exactly as decided: light tokens unchanged in
  `:root`, dark values in `[data-theme="dark"]` plus the
  `prefers-color-scheme` media entry, `color-scheme` flipped per entry, and
  dark twins inside both fallback override blocks. The tri-state controller
  (`frontend/src/app/theme.ts` + `ThemeSwitch.tsx`), the blocking pre-paint
  script in `index.html`, and the split `theme-color` metas match the
  decision text above.
- The executable guards are `frontend/src/app/themeTokens.contract.test.ts`
  (dark token drift guard: both dark entries and both fallback twins equal
  after normalization; index.html bootstrap mirrors the theme module) and
  `frontend/src/app/themeContrast.contract.test.ts` (dark contrast guard:
  WCAG ratios computed from `base.css` for every canonical text/background
  pair, AA ≥4.5:1 with the `muted-faint` floor pair ≥5.5:1). A Playwright
  workflow (`frontend/tests/e2e-ts/theme_selection.spec.ts`) covers the
  runtime contract: OS emulation, lock persistence across reload, light
  lock under a dark OS with the attribute applied before first paint, and
  live OS-following after returning to `system`.
- The two recorded raw-color exceptions were absorbed as named tokens with
  dark variants: the `studio-nav.css` badge family →
  `--badge-neutral-*` / `--badge-active-*`, and the `library.css` row-hover
  literal → `--library-row-hover`. The campaign's integration pass then
  tokenized the remaining badge literals the ledger had not listed:
  `--badge-deprecated-bg/ink` (light values `#f3e0dc` / `#8a4a3c`, dark
  pair reusing the dark danger family at 6.91:1) and the active-row draft
  variant `--badge-draft-active-bg/ink` (light `#d5dddd` / `#3d4647`, dark
  `#2f383a` / `#c7ced0` at 7.53:1). `base.css` is now the only file with
  raw colors.
