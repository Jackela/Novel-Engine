# Frontend skills configuration — 2026-09-10

## Task and fixed points

Owner asked for a survey of frontend-related agent skills (starting from
`google-labs-code/design.md`) and a working configuration for upcoming
frontend development. Plan approved in-session; execution delegated.

- Baseline `main`: `5fa8925c3a9446aa59a8a9b00d75576a1a1b0e37`.
- Pre-existing uncommitted `AGENTS.md` policy edit (authorization/red-lines
  wording) belongs to the Owner and is preserved verbatim; this change only
  appends the `### Frontend work` subsection under `## Agent skills`.
- Untracked `.zcode/` is harness state, untouched.

## Write set

| Path | Change |
|---|---|
| `DESIGN.md` | Migrated free prose → `@google/design.md` schema (YAML tokens + prose); fixed stale token pointer |
| `.agents/skills/web-design-guidelines/SKILL.md` | New; verbatim copy of `vercel-labs/agent-skills` skill (v1.0.0) |
| `.agents/skills/frontend-workflow/SKILL.md` | New; repo routing skill (stack facts + per-task skill routing) |
| `AGENTS.md` | Appended `### Frontend work` pointer only |
| `docs/agents/frontend-skills-2026-09-10.md` | This record |

Product source, dependencies, and configuration are untouched.

## DESIGN.md migration evidence

Executed per the `create-design-md` skill, repository mode. Governing sources:
`frontend/src/styles/base.css` (`:root` tokens, `ui-` primitives), the eight
feature CSS files, `frontend/src/index.css` conventions comment, the previous
`DESIGN.md` prose, and `@fontsource-variable/ibm-plex-sans` declarations.

- `npx @google/design.md lint DESIGN.md` → 0 errors, 14 warnings.
  Warnings are `missing-primary` (the governing source names the accent
  semantically `teal-strong`; no `primary` alias invented) and
  `orphaned-tokens` for surface/line/muted colors real in the product but not
  referenced by the five button/input components. Accepted as warnings, not
  forced away with synthetic tokens.
- `npx @google/design.md export --format dtcg DESIGN.md` → all 19 colors and
  4 typography scales emitted. `components` is not emitted by exporter
  v0.4.0 in any format; recorded as an exporter limitation, components kept
  (the skill forbids removing supported design information to satisfy an
  exporter).
- `npx @google/design.md diff <previous> DESIGN.md` → additions only; every
  accepted decision from the previous prose (typography identity, neutral +
  teal language, token reuse, dense panels, state completeness,
  reduced-motion) is preserved.

## Conflicts reported outside DESIGN.md

1. **Bundled font never applies.** `frontend/src/styles/base.css:22` declares
   `font-family: "IBM Plex Sans", system-ui, sans-serif`, but
   `@fontsource-variable/ibm-plex-sans` (imported in
   `frontend/src/main.tsx:4`) registers the family
   `'IBM Plex Sans Variable'` (verified in `node_modules`). The names do not
   match, so the UI renders the `system-ui` fallback while the variable font
   is downloaded but unused. `DESIGN.md` records the documented intent
   (IBM Plex Sans Variable). The fix is a one-line product change in
   `base.css` and needs its own task/authorization.
2. **Stale pointer (fixed).** The previous `DESIGN.md` located shared tokens
   in `frontend/src/index.css`; the real definition is
   `frontend/src/styles/base.css`. Corrected in the rewrite.

## Validation actually run

- `pnpm spec:validate` → 2 passed, 0 failed.
- `pnpm --dir server gates` → ssot aligned (0.6.0), repo-hygiene clean,
  file-size clean (691 files), migration-channel clean, llms-txt clean
  (21 links), OpenAPI snapshot 1/1 passed.
- Frontend `lint` / `type-check` / `test:unit` / `build` not run: no file
  under `frontend/` changed.
- CI not run: delivered as worktree diff, no commit created (AGENTS.md holds
  an unrelated Owner edit; a commit would need a path-scoped staging decision
  by the Owner).

## Skips and human gates

- No `package.json` dependency added; `@google/design.md` runs via `npx`
  ad hoc. Persistent gating (CI job for DESIGN.md lint/diff) would need its
  own authorization.
- Not installed, with reasons: anthropic `frontend-design` (overlaps
  impeccable; its deliberate-risk posture conflicts with consistency-first
  product UI), `theme-factory`/`canvas-design`/`web-artifacts-builder`
  (wrong scenario), Tailwind-centric skills (no Tailwind here).
- `impeccable` artifacts (PRODUCT.md, surface briefs, hooks) intentionally
  not created; `frontend-workflow` routes a first `impeccable` run through
  explicit authorization.
- Human gate open: harness discovery of the two new repo skills is expected
  in the next agent session; visual acceptance of DESIGN.md content is the
  Owner's review of the worktree diff.

## Survey sources

- design.md format + CLI: https://github.com/google-labs-code/design.md
- Stitch DESIGN.md announcement:
  https://blog.google/innovation-and-ai/models-and-research/google-labs/stitch-design-md/
- ibelick/ui-skills (create-design-md, improve-ui): https://github.com/ibelick/ui-skills
- vercel-labs/agent-skills (web-design-guidelines etc.): https://github.com/vercel-labs/agent-skills
- pbakaus/impeccable: https://github.com/pbakaus/impeccable
- anthropics/skills: https://github.com/anthropics/skills
