# Repository simplification evidence — 2026-09-08

## Candidate and scope

- Fixed baseline: `df44d957d4b244afdac3d060df293ff9828ca335`.
- Candidate: `ec6d21538d692afc4d80a463eca557e441f4935b`.
- Three commits: `93911e08` (dead beat helper and wiki reference),
  `12165677` (wiki reconciliation), `ec6d2153` (frontend scripts/config).
- Baseline-to-HEAD diff: 11 files, 18 insertions, 43 deletions.
- Existing product features are preserved. No dependency or lockfile changes.
- Product-removal candidates remain pending explicit selection. Generic wrappers
  and retry helpers were retained where simplification had weak net gain.
- Root `AGENTS.md` changes and `.zcode/` were pre-existing and excluded.

## Validation evidence

The source files were frozen before the candidate commits. Checks ran in the
shared working tree, not a clean isolated checkout of the candidate SHA;
therefore these are local working-tree results, not clean-SHA claims.

| Command | Result | Log |
| --- | --- | --- |
| `pnpm --dir server type-check` | pass | [`type-check`](/tmp/novel-engine-type-check-20260908.log) |
| `pnpm --dir server lint` | pass; one existing CookieJar warning at `server/tests/api/studio_structure_capacity_scalars.test.ts:14` | [`lint`](/tmp/novel-engine-lint-20260908.log) |
| `pnpm --dir server arch` | pass; 235 modules, 996 dependencies | [`arch`](/tmp/novel-engine-arch-20260908.log) |
| `pnpm --dir server gates` | pass | [`gates`](/tmp/novel-engine-gates-20260908.log) |
| `pnpm --dir server test` | pass; 212 files, 1324 tests | [`test`](/tmp/novel-engine-test-20260908.log) |
| `pnpm --dir frontend lint` | pass | [`frontend lint`](/tmp/ne-frontend-lint.out) |
| `pnpm --dir frontend format:check` | pass | [`frontend format`](/tmp/ne-frontend-format.out) |
| `pnpm --dir frontend type-check` | pass | [`frontend typecheck`](/tmp/ne-frontend-typecheck.out) |
| `pnpm --dir frontend test:unit` | pass; 103 files, 562 tests | [`frontend unit`](/tmp/ne-frontend-unit.out) |
| `pnpm --dir frontend build` | pass; build identity verified | [`frontend build`](/tmp/ne-frontend-build.out) |
| `pnpm --dir frontend test:e2e:smoke` | pass; 3 tests | [`e2e smoke`](/tmp/ne-frontend-e2e-smoke.out) |
| `pnpm spec:validate` | pass; 2/2 | recorded in task log |

Additional alias checks passed: `pnpm --dir frontend run test src/app/productBuildConfig.test.ts`
and `pnpm --dir frontend run test:unit src/app/productBuildConfig.test.ts` each ran 2/2 tests.
`pnpm --dir frontend run test:e2e --list` and
`pnpm --dir frontend run test:e2e:ts --list` each listed 23 tests in 8 files.
An accidental `-- --list` invocation ran the full E2E suite (23 pass) twice;
this was an invocation error, not intentional extra assurance.

## Review and residual gates

- Standards review of tools/backend diff: clean. Wiki changes were excluded
  from independent author review because the wiki author reviewed that scope.
- Independent Spec review found stale `tsconfig.node` and wiki references;
  both were fixed and the rereview passed.
- API-types drift, React Doctor, container persistence, hosted CI, push,
  human acceptance, and release authorization were not run. They remain open
  with the integrator/owner and must close on the final candidate before release.

This record is a documentation-only follow-up to the candidate above.

## Wave 2 evidence

- Fixed baseline: `1617eeec5856ebc067dbd18b9b325cf6dd648947`.
- Candidate: `c4c7b062b4b10b59b38fe887991e82981215afac`; commits `37313ea7`
  (remove two dead helpers, 38 lines) and `c4c7b062` (daily usage parser fix,
  17 production lines and 73 lines of regression tests).
- Scope was limited to the two proven dead backend helpers and the frontend
  usage contract boundary. No product-cut decisions or dependency changes.
- Working-tree validation was not clean-SHA validation; user `AGENTS.md` and
  `.zcode/` changes were excluded. No push or release action occurred.
- Server baseline/targeted three-file review, type-check, lint, arch, gates,
  and test evidence is recorded in `/tmp/wave2-server-*.log` (full run:
  212 files, 1324 tests); lint retained the existing CookieJar warning.
- Frontend evidence is in `/tmp/ne-usage-{unit,typecheck,build,api-types,server-sizes}.out`;
  full frontend tests passed 104 files / 567 tests; corrected targeted usage
  tests passed 5/5, with corrected lint/format logs.
  The full frontend suite was not repeated after the assertion-only change.
- The red run `/tmp/ne-usage-red.out` had three failures, including one
  over-strict legacy optional-key assertion. The fix preserves normal daily
  usage and rejects malformed responses. Stricter frontend safe-integer/date
  checks were reviewed and deferred because backend canonical validation and
  existing `numberField` semantics remain authoritative.
- Browser/CI/container/React Doctor checks were not rerun this wave. Final
  integration review and release authorization remain open.
