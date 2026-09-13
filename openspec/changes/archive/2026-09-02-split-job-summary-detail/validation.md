# Validation evidence

## Fixed points

- Comparison SHA: `3389a694a87e36894b9ffaa68a40190e234d84bf`
- Change proposal SHA: `7af0e62b51bdf3ac4b0130b2610c3c73cedced70`
- Router-contract correction SHA: `5a7bc1cc6e70fd1f78ed2c331755c40fe91a1357`
- Local implementation candidate SHA: `5e2290f54d4469414f7c55580a7514e1041b7f27`
- Environment: Darwin arm64, Node.js 24.19.0, pnpm 11.6.0

## Targeted and review evidence

The integrated server target set passed 14 files and 68 tests. It covered the
strict twelve-field summary, full scoped detail, oldest-first detail events,
normalized project/job misses, schema-before-auth parameter bounds, retry and
proposal/review/export bridges, pagination, transaction behavior, a 32,767-job
history, production query plans, and an actual public-store SQL trace proving
zero `job_events` reads. Malformed large JSON bodies were deliberately stored;
the summary read succeeded without parsing them.

The integrated frontend target set passed 8 files and 52 tests before review.
It covered exact-key and closed-enum parsing, real UTC calendar validation,
pagination and project ownership, retry refresh, audit and whole-book fresh
first-page reads, and the absence of implicit detail requests. The final review
regression added a component test proving failed or interrupted import jobs do
not expose the server-forbidden Retry action; that file then passed 8 of 8.

Three independent read-only reviews crossed the server, store, OpenAPI,
generated types, and frontend boundaries. They found no P0 or P1 issue. Two
findings were closed before the candidate was fixed:

- a stale server test title still described events on the list response; it now
  names newest-first summaries and oldest-first detail events;
- the panel initially offered Retry for failed/interrupted import summaries,
  although imports are not retryable; eligibility now excludes imports and has
  a focused regression test.

Agent consensus is supporting review evidence only; it is not CI or human
acceptance.

## Local full evidence

All successful commands below ran against the clean committed tree at
`5e2290f54d4469414f7c55580a7514e1041b7f27`.

| Command | Result |
|---|---|
| `pnpm --dir server exec vitest run --maxWorkers=4` | Passed: 143 files and 1,024 tests in 119.58 seconds. |
| `pnpm --dir server gates` | Passed; SSOT, hygiene, 488-file size budget, migration channel, 19 llms-txt links, and OpenAPI snapshot were clean. |
| `pnpm --dir server type-check` | Passed. |
| `pnpm --dir server lint` | Passed; 340 files checked with no fixes. |
| `pnpm --dir server arch` | Passed; 192 modules and 792 dependencies had no violation. |
| `pnpm --dir server build` | Passed. |
| `pnpm --dir frontend test:unit` | Passed: 64 files and 353 tests in 20.65 seconds. |
| `pnpm --dir frontend lint` | Passed; 174 files checked with no fixes. |
| `pnpm --dir frontend format:check` | Passed; 173 files checked with no fixes. |
| `pnpm --dir frontend type-check` | Passed. |
| `pnpm --dir frontend check:api-types` | Passed; generated types match the OpenAPI snapshot. |
| `pnpm --dir frontend build` | Passed; 1,911 modules built and Novel Engine 0.6.0 identity was verified in HTML and seven JavaScript bundles. |
| `pnpm test:e2e:full-audit` from `frontend/` | Passed: all 8 Chromium workflows in 22.1 seconds. |
| `pnpm spec:validate --strict` | Passed: seven active changes plus the canonical specification, 8 of 8 items. |

## Archive status

This completed local change remains **active and not archived**. Required CI
has not run on the implementation candidate. Pagination must be archived first;
the canonical specification must then be revalidated before this change is
archived. Detail UI, event pagination, and attempt correlation remain explicit
non-goals rather than silently claimed follow-up work.

## External and human gates

- GitHub required checks: **not run** because this task did not push or open a
  pull request. Owner: repository maintainer. Closure: every required context is
  green on the exact candidate SHA.
- Cross-platform execution: **not run** outside this Darwin arm64 host. Owner:
  release maintainer. Closure: required CI records its platform matrix and SHA.
- Human acceptance: **not run** and not implied by automated accessibility or
  agent review. Owner: product/release maintainer. Closure: an author confirms
  the summary history remains useful and the absence of Retry on imports is
  understandable.
