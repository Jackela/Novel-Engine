# Tasks

Dependency graph: `T1` is the foundation and blocks everything. `T2a`,
`T2b`, `T2c`, `T2d` are file-disjoint implementation batches blocked only
by `T1`; they may run in parallel. `T3` is integration and gates, blocked
by all of `T2a`–`T2d`. File ownership is exclusive per batch: T1 owns
`base.css`, `index.html`, and all new `frontend/src/app/theme*` files;
T2a owns `entry.css`, `library.css`, `EntryPage.tsx`,
`ProjectLibraryPage.tsx` (+ their tests); T2b owns `studio-nav.css`,
`StudioTopbar.tsx`, `StudioNavigator.tsx` (+ their tests); T2c owns
`editor.css`, `inspector.css`, `MarkdownEditor.tsx`, `StudioEditorPane.tsx`,
`StudioInspector*.tsx` (+ their tests); T2d owns `layout.css`, `usage.css`,
`StudioPageView.tsx`, `StudioStatusbar.tsx` (+ their tests).

## T1: Dual-theme token and selection foundation

- [x] T1.1 Add the dark token set to `frontend/src/styles/base.css` as the
      dual entry (`[data-theme="dark"]` plus
      `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) }`),
      using the draft table in `design.md`; declare `color-scheme: light`
      on `:root` and `color-scheme: dark` in both dark entries. Acceptance:
      `pnpm --dir frontend test:unit -- theme` green.
- [x] T1.2 Add dark twins inside the existing
      `@media (prefers-reduced-transparency: reduce)` and
      `@supports not (backdrop-filter…)` override blocks (near-opaque dark
      fills, blur 0, solid borders, no shadow). Acceptance: CSSOM parse
      assertions in the token drift-guard test pass.
- [x] T1.3 Pre-declare the badge-family tokens (`--badge-neutral-bg`,
      `--badge-neutral-ink`, `--badge-active-bg`, `--badge-active-ink`) and
      the project-row hover token (`--library-row-hover`) in `base.css`
      with light and dark values, so T2a/T2b replace literals without
      touching `base.css`. Acceptance: unit suite green; tokens present in
      both `:root` and both dark entries.
- [x] T1.4 Add the blocking inline theme script to `frontend/index.html`
      (stored `light`/`dark` lock applied to `documentElement.dataset.theme`
      before first paint; `system`/absent/unreadable does nothing) and split
      `theme-color` into two metas with `media` attributes
      (`#d9eee9` light, `#122b28` dark). Acceptance: `pnpm --dir frontend
      build` succeeds; manual load shows no first-paint flash in either OS
      emulation.
- [x] T1.5 Add the theme controller `frontend/src/app/theme.ts` (tri-state
      read/write of the `novel_engine_theme` localStorage key, silent
      fallback to `system` on any storage error, `matchMedia` listener that
      re-applies `data-theme` only while unlocked, `theme-color` override on
      locks) and `frontend/src/app/ThemeSwitch.tsx` (three-state segmented
      control, 44px target, visible focus, `ui-theme-switch` styles in
      `base.css`) with unit tests covering lock persistence, OS-follow,
      light-under-dark-OS, and storage-failure fallback. Acceptance:
      `pnpm --dir frontend test:unit -- theme` green.
- [x] T1.6 Add the executable guards: a drift-guard test asserting the two
      dark token blocks (and both dark fallback blocks) are equal after
      normalization, and a contrast test computing WCAG ratios from
      `base.css` values for the canonical text/background pairs, asserting
      AA 4.5:1 with the `muted-faint` floor pair at ≥5.5:1 per `design.md`.
      Acceptance: `pnpm --dir frontend test:unit -- theme` green and the
      recorded contrast table matches the draft table within ±0.2.

## T2a: Entry and project library dark pass (blocked by T1)

- [ ] T2a.1 Mount `ThemeSwitch` on `EntryPage` and `ProjectLibraryPage`;
      replace the `.library__project-row:hover` `#8dbab6` literal with
      `var(--library-row-hover)` in `library.css`. Acceptance:
      `pnpm --dir frontend test:unit -- EntryPage ProjectLibraryPage` green.
- [ ] T2a.2 Verify both surfaces auto-follow in light and dark (tokens only;
      add dark fixes only where a literal proves necessary, staying inside
      the batch's file ownership). Acceptance: browser check on a running
      stack — entry panel and library rows render correctly in both themes.

## T2b: Studio navigation chrome dark pass (blocked by T1)

- [ ] T2b.1 Mount `ThemeSwitch` in `StudioTopbar`; replace the
      `studio-nav.css` badge-family literals (`#e2e8e8`, `#5a6465`,
      `#cfe4e2`, `#0f6862`) with the T1 badge tokens, preserving the
      in-file AA rationale as token comments. Acceptance:
      `pnpm --dir frontend test:unit -- StudioNavigator StudioTopbar`
      green.
- [ ] T2b.2 Verify navigator, badges, and top bar in both themes, including
      the one-glass-layer rule intact. Acceptance: browser check — no blur
      nesting, badges AA in both themes per the T1 contrast test values.

## T2c: Editor and inspector dark pass (blocked by T1)

- [ ] T2c.1 Verify `editor.css` and `inspector.css` surfaces auto-follow;
      fix any dark-specific issue within the batch's files only (expected:
      none — both files are token-only today). Acceptance:
      `pnpm --dir frontend test:unit -- Editor Inspector` green.
- [ ] T2c.2 Verify the CodeMirror editor renders dark through the existing
      token theme and stays opaque. Acceptance: browser check — CM text,
      caret, selection, and focus all follow the dark tokens; no
      `backdrop-filter` on the editor surface.

## T2d: Layout shell and usage dark pass (blocked by T1)

- [ ] T2d.1 Verify `layout.css` and `usage.css` surfaces auto-follow
      (status bar, usage panel, grid shell); fix any dark-specific issue
      within the batch's files only. Acceptance:
      `pnpm --dir frontend test:unit -- Statusbar StudioPage` green.
- [ ] T2d.2 Verify the compact single-column layout and usage panel in both
      themes. Acceptance: browser check at the compact breakpoint — no
      unreadable hairline or status text in either theme.

## T3: Integration, gates, and design SSOT (blocked by T2a–T2d)

- [ ] T3.1 Add the Playwright theme workflow
      `frontend/tests/e2e-ts/theme_selection.spec.ts`: select dark, reload,
      dark persists; select light under dark-OS emulation, light renders;
      reset to system, OS preference decides. Acceptance:
      `pnpm --dir frontend test:e2e-ts -- theme_selection` green.
- [ ] T3.2 Live-switch browser acceptance across all surfaces (entry →
      library → studio → editor → usage) in one session: no flash, no
      light-only surface, reduced-transparency and no-`backdrop-filter`
      emulations hold in dark. Acceptance: recorded browser run against a
      local stack.
- [ ] T3.3 Update root `DESIGN.md` per the `design.md` representation
      (frontmatter untouched, `## Dark theme values` appendix added) and run
      the gates. Acceptance: `npx @google/design.md lint DESIGN.md` 0
      errors; `npx @google/design.md diff` reviewed and recorded.
- [ ] T3.4 Flip `docs/adr/0010-dual-theme-token-architecture.md` to
      `status: accepted`. Acceptance: ADR status updated in the same
      series.
- [ ] T3.5 Run the full owning gates and record evidence:
      `pnpm --dir frontend lint && pnpm --dir frontend format:check &&
      pnpm --dir frontend type-check && pnpm --dir frontend test:unit &&
      pnpm --dir frontend build`, plus `pnpm spec:validate` after the change
      folder lands. Acceptance: all green; evidence recorded per
      `docs/agents/change-evidence.md`.
