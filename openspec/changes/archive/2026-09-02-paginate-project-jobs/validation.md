# Validation evidence

## Fixed points

- Comparison SHA: `18bf9ed3802dafdc922d3fbeb7f76ccc97b77bbb`
- Change proposal SHA: `044aca999632207dcbf850bf56108280702ad6f8`
- Local implementation candidate SHA: `93eeca57209caef755662b9aeeab2fdda556449e`
- Environment: Darwin arm64, Node.js 24.19.0, pnpm 11.6.0

## Targeted evidence

The final integrated server target set passed 5 files and 27 tests. It covered
the existing synchronous jobs contract, default 50 and maximum 100 HTTP pages,
invalid limits, canonical and project-bound cursor validation, equal-timestamp
keyset traversal, boundary deletion, concurrent newer insertion, direct-store
limit enforcement, transaction behavior, export callers, and a 32,767-job
history. Query-plan assertions execute the SQL and parameters produced by the
same Drizzle builders used in production and prove tuple-range composite-index
search plus indexed event ordering without temporary sorts.

The final integrated frontend target set passed 15 files and 87 tests. It
covered strict `next_cursor` parsing, query encoding, first-page replacement,
older-page append and both cross-page and within-page de-duplication,
same-cursor coalescing, fresh-request precedence, failure preservation, project
ownership and inspector laziness, accepted-proposal and retry refresh wiring,
unknown-outcome audit ownership, and the accessible load-older busy, terminal,
failure, and focus states.

Three read-only audit agents reviewed the initial specification and two
implementation passes. Findings closed before the candidate was committed:

- a normally valid-looking cursor could have multiple JSON encodings; decode
  now requires complete canonical re-encoding equality and tests whitespace,
  exponent, and escaped-string alternatives;
- the first query-plan test copied SQL instead of exercising production query
  construction; production and evidence now share narrow infrastructure query
  builders;
- high-cardinality test databases were not removed; every harness path now
  closes SQLite before deleting its temporary directory;
- audit failure briefly polluted the generic Jobs error owner; it again remains
  owned by the established audit-failed gate;
- one older page could contain duplicate ids; append now updates its seen-id set
  for every accepted item;
- HTTP default/max positive boundaries and several audit/older concurrency
  outcomes received explicit regression coverage.

Final follow-up reviews reported no P0 or P1 finding. Agent consensus is
supporting review evidence only; it is not CI or human acceptance.

## Local full evidence

All successful commands below ran against the clean committed tree at
`93eeca57209caef755662b9aeeab2fdda556449e`.

| Command | Result |
|---|---|
| `pnpm --dir server exec vitest run --maxWorkers=4` | Passed: 141 files and 1,014 tests in 104.79 seconds. |
| `pnpm --dir server gates` | Passed; SSOT, hygiene, 486-file size budget, migration channel, 19 llms-txt links, and OpenAPI snapshot were clean. |
| `pnpm --dir server type-check` | Passed. |
| `pnpm --dir server lint` | Passed; 338 files checked with no fixes. |
| `pnpm --dir server arch` | Passed; 192 modules and 791 dependencies had no violation. |
| `pnpm --dir server build` | Passed. |
| `pnpm --dir frontend test:unit` | Passed: 64 files and 342 tests in 16.18 seconds. |
| `pnpm --dir frontend lint` | Passed; 174 files checked with no fixes. |
| `pnpm --dir frontend format:check` | Passed; 173 files checked with no fixes. |
| `pnpm --dir frontend type-check` | Passed. |
| `pnpm --dir frontend check:api-types` | Passed; generated types match the OpenAPI snapshot. |
| `pnpm --dir frontend build` | Passed; 1,911 modules built and Novel Engine 0.6.0 identity was verified in HTML and seven JavaScript bundles. |
| `pnpm test:e2e:full-audit` from `frontend/` | Passed: all 8 Chromium workflows, including whole-book generation and job accounting, in 21.5 seconds. |
| `pnpm spec:validate --strict` | Passed: six active changes plus the canonical specification, 7 of 7 items. |

An initial attempt ran only `whole_book.spec.ts`. That file deliberately logs
into the Owner created by the earlier `studio-ts.spec.ts`; isolated execution
therefore remained on `Create the local owner` and timed out before any product
workflow. No source or test was changed. The repository-owned complete E2E
sequence then passed all eight workflows as recorded above. This invocation
error is retained here and is not presented as a product failure or an initial
green result.

The first frontend static command group used the nonexistent script name
`api-types:check` after lint, format, and type-check had passed. The command
failed before type drift or build ran. The live package manifest names that
script `check:api-types`; the exact repository-owned command and production
build were then run successfully. No source was changed between attempts.

## Archive status

This completed change remains **active and not archived**. Required CI has not
run on the implementation candidate. Owner: repository maintainer. Closure:
every live required check passes on the exact integration SHA, strict OpenSpec
validation is rerun against the then-current canonical specification, and the
change is archived through the repository workflow.

Compact `JobSummary` plus scoped Job detail and attempt-correlated unknown-
outcome audit remain separate findings. This pagination change does not claim
to close either byte-size or attempt-identity risk.

## External and human gates

- GitHub required checks: **not run** because this task did not push or open a
  pull request. Owner: repository maintainer. Closure: every live required
  context is green on the exact integration SHA.
- Cross-platform SQLite and browser execution: **not run** outside this Darwin
  arm64 host. Owner: release maintainer. Closure: required CI exercises its live
  platform matrix and records the exact candidate SHA.
- Human acceptance: **not run** and not implied by automated accessibility
  tests or agent review. Owner: product/release maintainer. Closure: an author
  confirms Refresh versus Load older is understandable, keyboard focus remains
  predictable, and paged history suits the real project workflow.
