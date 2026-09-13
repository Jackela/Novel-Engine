# Replace exact-token-duplicate color literals with tokens

Written against: 11b4e5ef

## Evidence chain

- Surface: Studio three-pane workspace + entry/library chrome (`frontend/src/styles/*.css`)
- Problem: 25 color literals are byte-for-byte identical to existing `:root` tokens in `frontend/src/styles/base.css`, bypassing the token system while sibling rules in the same files already use the token form.
- Design evidence: root `DESIGN.md` (Colors): "components reuse those tokens instead of introducing one-off colors"; token owners `frontend/src/styles/base.css:11,13,14`.
- Owner: `frontend/src/styles/base.css` (`:root` custom properties)
- Scope and affected surfaces:
  - `#dfe2e3` == `--line` (20×): editor.css:93; inspector.css:5,47; layout.css:4,82,90,131,144; usage.css:12,34,90,131; library.css:8,66,92; studio-nav.css:22,41,129,147
  - `#626a6b` == `--muted-soft` (6×): editor.css:39,70; entry.css:84,97; library.css:123,128
  - `#697172` == `--muted-faint` (1×): inspector.css:249
- Uncertainty: none — replacements are value-identical by definition; rendered output cannot change.

## Design decision

Replace each listed literal with `var(--<token>)` for its exact-match token. This is a mechanical, zero-visual-diff refactor that restores the documented single source of truth for color values.

## Reuse

- `var(--line)`, `var(--muted-soft)`, `var(--muted-faint)` from `frontend/src/styles/base.css`
- Exemplar: `studio-nav.css:54` (`border-bottom: 1px solid var(--line)`) — same file already uses the token for the identical hairline purpose.

## Changes

1. `frontend/src/styles/` (the eleven occurrences' files listed above)
   - Change: literal → matching `var(--…)` at exactly the cited lines; no other edits.
   - Preserve: every other literal that does NOT exactly match a token (e.g. `#4f595a`, `#0f6862`, `#e1e4e5`) — near-matches are out of scope and must not be "rounded" to tokens.
   - Verify: `grep -n '#dfe2e3\|#626a6b\|#697172' frontend/src/styles/*.css` returns only `base.css` token definitions.

## Scope

- Inherit: all surfaces rendering these borders/text (studio panes, statusbar, usage tables, library cards, entry panel) — identical computed values.
- Verify: frontend build; browser spot-check of studio chrome.
- Exclude: near-match literals (different values); `base.css` token definitions themselves.

## Validation

- Product: studio/library/entry render pixel-identical (value-equal substitution).
- Interface: entry page, library page, studio three panes, usage tab.
- System: no parallel color pathway remains for these three values.
- Repository: `pnpm --dir frontend lint && pnpm --dir frontend build` → clean; unit tests `pnpm --dir frontend test:unit` → 567 pass.

## Stop conditions

- Stop if any replacement target line no longer contains the exact literal (file drifted); re-audit instead of guessing.

## Design documentation

- After acceptance and validation: none — the rule already exists in `DESIGN.md`; this plan merely conforms implementation.
