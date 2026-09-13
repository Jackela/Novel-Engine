# Validation evidence

## Candidate

- Baseline: `87caa06480627b87121f331768da5de9222f2b41`
- Candidate: `dd299f8901cd596a506f7a59c13c146142853d0a`
- Environment: local macOS workspace, Chromium browser workflows

## Targeted and local-full evidence

| Surface | Exact command | Result |
|---|---|---|
| Entry and library lifecycle components | `pnpm --dir frontend exec vitest run --config vitest.config.ts src/features/studio/EntryPage.lifecycle.test.tsx src/features/studio/ProjectLibraryPage.lifecycle.test.tsx src/features/studio/ProjectLibraryPage.actions.test.tsx` | Passed: 3 files, 25 tests. |
| Frontend lint | `pnpm --dir frontend lint` | Passed: 163 files, no fixes. |
| Frontend format | `pnpm --dir frontend format:check` | Passed: 162 files. |
| Frontend types | `pnpm --dir frontend type-check` | Passed. |
| Frontend unit suite | `pnpm --dir frontend test:unit` | Passed: 57 files, 297 tests. |
| Production build | `pnpm --dir frontend build` | Passed; product identity verified in HTML and seven JavaScript bundles. |
| Generated API contract | `pnpm --dir frontend check:api-types` | Passed: generated types match the frozen OpenAPI snapshot. |
| React static diagnostics | `pnpm --dir frontend exec react-doctor --json` with the CI zero-diagnostic parser | Passed: score 100, zero diagnostics. |
| File-size policy | `pnpm --dir server gate:sizes` | Passed: 432 files, no legacy baselines. |
| Product specification | `pnpm spec:validate` | Passed: active change and canonical specification. |
| Browser workflows | `pnpm --dir frontend test:e2e:full-audit` | Passed: 8 Chromium workflows. |

The final independent read-only review examined the candidate-equivalent entry
and library implementation after the shared command-owner correction and found
no remaining P0-P3 issue. The integrator then reviewed the complete staged diff
and reran the applicable checks above on the fixed candidate SHA.

## Open gates and scope boundaries

- Required GitHub CI: **not run**. The candidate has not been pushed; local
  evidence does not claim branch-protection completion. Owner: repository
  maintainer. Closure: run every required context on the exact integration SHA.
- Human keyboard and screen-reader acceptance: **not run**. Component tests and
  Chromium workflows cover focus and accessible state mechanically but do not
  replace human assistive-technology judgment. Owner: product/release owner.
  Closure: exercise entry failure/retry, first-run setup, project-list failure,
  project creation, and logout on the release candidate.
- Container persistence: **not applicable to this frontend-only lifecycle
  change**; no container, database, migration, or persistence contract changed.
