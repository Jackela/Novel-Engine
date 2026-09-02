# Validation evidence

## Fixed points

- Comparison SHA: `0ff451bad9d4fcbef5f3a224de725bdd0c0b72c2`
- Change proposal SHA: `b61792aea1a36ce139b6507feafda5fc1bc8556a`
- Local implementation candidate SHA: `76f96bd4a3c3757c67052e83805d2243b330df39`
- Environment: Darwin 27.0.0 arm64, Node.js 24.19.0, pnpm 11.6.0

## Targeted evidence

The integrated candidate passed 26 directly affected permit, admission,
configuration, error, OpenAPI, deletion, retry, export, Provider-cleanup, and
stream-lifecycle files with 99 tests. Additional independent SSE cleanup
checks then covered a never-started aborted stream, primary plus generator
cleanup failure, and test-helper cleanup failure. The final focused SSE set
passed 4 files and 23 tests.

The API admission matrix exercised all five counted POST families against real
Fastify injection and temporary SQLite. A blocked app returned ordinary JSON
503 responses with the exact capacity envelope and `Retry-After: 5`; Provider
construction, artifact writes, and job, event, usage, snapshot, snapshot
document, review, review issue, export, and cleanup-intent counts did not
change. Per-project refusal, application refusal, conflict priority, idle
project deletion, and recovery after release were also exercised.

Cleanup-lifetime tests held capacity through Provider disposal, review
evaluation, proposal retry disposal, fresh-export acknowledgement, export
rollback, export-retry acknowledgement, terminal SSE backpressure, disconnect,
generator return, and combined primary/cleanup errors. The token-bound guard
tests covered default and injected limits, failed-acquire immutability,
idempotent release, stale permit release, and project-exclusive ownership.

Independent review first found one P1: a normally drained terminal stream
released its permit before response-end and connection-listener cleanup. The
application now returns an explicit stream session, and the response writer
releases it only after generator and connection cleanup. Follow-up review found
no product-code P0-P3 issue; its P2 evidence gap for never-started and cleanup
failure branches was closed with failing-then-passing regression tests.
Independent protocol review found one P3 temporary-directory leak in a new
configuration test; cleanup was added. The final frontend review found no
P0-P3 issue and passed 8 focused files with 65 tests, confirming that capacity
503 remains a known `HttpError`, does not enter unknown-outcome audit state,
and never triggers automatic retry. Agent reports are supporting evidence, not
CI or release approval.

## Local full evidence

All successful commands below ran against the clean committed tree at
`76f96bd4a3c3757c67052e83805d2243b330df39`.

| Command | Result |
|---|---|
| `pnpm --dir server exec vitest run --maxWorkers=4` | Passed: 139 files and 1,003 tests in 111.95 seconds. |
| `pnpm --dir server gates` | Passed; SSOT, hygiene, 480-file size budget, migration channel, 19 llms-txt links, and OpenAPI snapshot were clean. |
| `pnpm --dir server type-check` | Passed. |
| `pnpm --dir server lint` | Passed; 334 files checked with no fixes. |
| `pnpm --dir server arch` | Passed; 189 modules and 778 dependencies had no violation. |
| `pnpm --dir server build` | Passed. |
| `pnpm --dir frontend test:unit` | Passed; 62 files and 325 tests in 17.06 seconds. |
| `pnpm --dir frontend lint` | Passed; 172 files checked with no fixes. |
| `pnpm --dir frontend format:check` | Passed; 171 files checked with no fixes. |
| `pnpm --dir frontend type-check` | Passed. |
| `pnpm --dir frontend check:api-types` | Passed; generated API types match the OpenAPI snapshot. |
| `pnpm --dir frontend build` | Passed; 1,911 modules built and Novel Engine 0.6.0 identity was verified in HTML and seven JavaScript bundles. |
| `pnpm spec:validate` | Passed in strict mode; five active changes plus the canonical specification, 6 of 6 items. |

The first exact `pnpm --dir server test` attempt overcommitted the local host.
Seven unrelated API files reported long timeouts and the test process then
disappeared before a final summary. No assertion, timeout, or production code
was changed. Those seven files passed alone with one worker, 7 files and 53
tests in 66.86 seconds. The complete unchanged suite then passed with four
workers as recorded above. This resource-contention run remains recorded and
is not presented as an initial green result.

## Archive status and ordering

This completed change remains **active and not archived**. Required CI has not
run on the integration candidate. The overlapping
`2026-09-02-fail-loud-env-local-loading` change MUST archive first after CI is
green. This capacity change is then revalidated against the resulting canonical
specification and archives second. Owner: repository maintainer. Closure: every
live required check passes on the exact integration SHA, the fail-loud change
archives first, strict validation is rerun, and this change then archives.

## External and human gates

- GitHub required checks: **not run** because this task did not push or open a
  pull request. Owner: repository maintainer. Closure: every live required
  context is green on the exact integration SHA.
- Browser and Playwright workflows: **not run** in this change-local evidence.
  Fastify injection and frontend units cover the error channel and no-auto-retry
  behavior, but not a real browser under saturation. Owner: integrator. Closure:
  the final repository validation wave runs the current Playwright workflows
  against the TypeScript backend.
- Target-host load and proxy behavior: **not run**. Node response-boundary tests
  cover SSE drain and disconnect ownership, but host scheduling and proxy
  buffering remain external. Owner: deployment maintainer. Closure: a target
  deployment confirms immediate refusal and bounded in-flight work under burst
  load without changing the app-local policy.
- Human acceptance: **not run** and not implied by agent consensus or automated
  tests. Owner: product/release maintainer. Closure: an author confirms capacity
  errors are understandable, require an explicit retry, and do not disrupt
  ordinary proposal, review, export, or retry workflows.
