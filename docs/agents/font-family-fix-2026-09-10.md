# Font family fix — 2026-09-10

## Root cause and change

`frontend/src/main.tsx` imports `@fontsource-variable/ibm-plex-sans`, whose
only declared `@font-face` family is `'IBM Plex Sans Variable'` (verified in
`node_modules/@fontsource-variable/ibm-plex-sans/index.css`). The stylesheet
applied `"IBM Plex Sans"` (`frontend/src/styles/base.css:22`), which matches
no declared face — CSS family matching is exact — so every UI render fell
through to the `system-ui` fallback while the variable font was downloaded
but never used. Found during the DESIGN.md migration recorded in
`docs/agents/frontend-skills-2026-09-10.md`.

Fix: one line in `frontend/src/styles/base.css` —
`"IBM Plex Sans"` → `"IBM Plex Sans Variable"`. This restores the documented
intent already recorded in `DESIGN.md` (typography.sans).

## Validation

- `pnpm --dir frontend lint` / `format:check` / `type-check` — clean.
- `pnpm --dir frontend test:unit` — 567/567 passed (104 files).
- `pnpm --dir frontend build` — success, build identity 0.6.0 verified.
- Browser check (main-session Playwright against `pnpm dev --port 5199`):
  - `getComputedStyle(document.body).fontFamily` →
    `"IBM Plex Sans Variable", system-ui, sans-serif`.
  - `[...document.fonts]` declares exactly one webfont family:
    `IBM Plex Sans Variable`; `document.fonts.status === "loaded"`.
  - Metric probe: `"IBM Plex Sans Variable"` renders `Ax` at 18.375px vs
    `system-ui` 18.46875px at the same size — rendering differs from the
    fallback, so the webfont is genuinely applied.
  - Screenshot: `font-fix-entry-2026-09-10.png` (entry surface).
  - Note: `document.fonts.check('16px "IBM Plex Sans"')` returns `true` on
    the old name as well because unknown families resolve synchronously to
    system fonts; the exact-match face list above is the probative evidence
    for the pre-fix fallback behavior.
  - Console errors on this page are the expected no-backend API failures of
    a frontend-only dev server; page chrome renders from `base.css`.

## Scope

Single-line product change; no spec/capability change, so no OpenSpec
change. Visual appearance intentionally changes from the system fallback to
the bundled product font (documented design intent).
