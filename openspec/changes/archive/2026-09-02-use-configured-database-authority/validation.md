# Validation evidence

## Fixed points

- Comparison SHA: `329196b86d6c6588f0e8a47228a8d1c996f583f1`
- Implementation SHA: `e82c765bfeec70e6e36c983a20ea1c56c8e5ebbd`
- Final local candidate SHA: `3c54f7fa025e446a2e521f82c32156d1bab13656`
- Environment: Darwin 27.0.0 arm64, Node.js 24.19.0, pnpm 11.6.0

## Targeted evidence

Command:

```text
pnpm --dir server exec vitest run tests/db/configured_database_authority.test.ts tests/api/database_authority.test.ts tests/apps/cli/cli_database_authority.test.ts tests/infrastructure/sqlite_health_probe.test.ts tests/api/health.test.ts
```

Result on the final local candidate: passed, 5 files and 20 tests. This covers
the exact configured basename across API and CLI entry points, fail-closed
legacy-sibling ambiguity before side effects, and open, closed, injected, and
database-free health-probe behavior.

An independent read-only closure review examined path ownership, lock ordering,
error classification, and readiness semantics. The final review reported no
remaining P0-P3 finding. Agent review is supporting evidence, not a validation
gate.

## Local full evidence

| Command | Result |
|---|---|
| `pnpm --dir server test` | Passed on the final local candidate; 124 files and 924 tests in 269.56 seconds. |
| `pnpm --dir server gates && pnpm --dir server arch && pnpm --dir server type-check && pnpm --dir server lint && pnpm --dir server build` | Passed; all repository gates were clean, 182 modules and 762 dependencies had no architecture violation, 310 files passed lint, and the server built. |
| `pnpm --dir frontend lint && pnpm --dir frontend format:check && pnpm --dir frontend type-check && pnpm --dir frontend test:unit && pnpm --dir frontend build && pnpm --dir frontend check:api-types` | Passed; 57 files and 297 tests, production identity, formatting, types, build, and generated API drift were clean. |
| `pnpm --dir frontend test:e2e:ts` | Passed; 8 Chromium workflows against the emitted TypeScript server. |
| `pnpm --dir frontend exec react-doctor --json` | Passed; 0 diagnostics, score 100. |
| `pnpm spec:validate` | Passed in strict mode for both active changes and the canonical specification. |
| `pnpm audit --audit-level high --prod` | Passed; no known production dependency vulnerabilities. |

The pre-harness candidate's default server test command exhausted host-reported
parallelism and produced 5-second timeout-only failures without assertion
differences. Commit `3c54f7fa025e446a2e521f82c32156d1bab13656`
bounded Vitest to two workers and set an explicit finite 10-second test budget.
The focused four-file stress set then passed three consecutive default runs
(36 tests each), and the full default command passed twice, including the
fixed-SHA result above. This closes the local harness finding only.

## External and human gates

- Docker container persistence/restart/deep-link validation: **not run** because
  the local host has no Docker executable. Residual risk is Linux container and
  volume behavior. Owner: repository CI. Closure: the `container` workflow job
  passes on the final review SHA.
- GitHub required checks: **not run** because this local task did not push or
  open a pull request. Residual risk is CI-only platform behavior and the
  15-minute server-job budget on Linux. Owner: repository maintainer. Closure:
  every live required check is green on the integration SHA.
- Human acceptance: **not run** and not represented as approved. The change is
  operational persistence/readiness behavior; browser automation and agent
  review are supporting evidence only. Owner: release maintainer. Closure:
  explicit human release approval if the target release requires it.
