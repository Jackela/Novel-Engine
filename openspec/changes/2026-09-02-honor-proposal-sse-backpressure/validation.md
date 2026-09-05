# Validation evidence

## Fixed points

- Change proposal SHA: `08de12e4cba6b7b38ba09465ebc4bf2cca69d86b`
- Server implementation SHA: `50f16e00469b649d3914d5b6c88d6435f966caa4`
- Final local code candidate SHA: `0cac0b5033152fb9237eedff7dc93f65d6f2c37d`
- Environment: Darwin 27.0.0 arm64, Node.js 24.19.0, pnpm 11.6.0

## Targeted evidence

The committed server candidate passed the response-writer, disconnect,
resource-lifecycle, and application-landing suites:

```text
pnpm --dir server exec vitest run tests/api/proposal_stream_response.test.ts tests/api/studio_proposals_disconnect.test.ts tests/api/proposal_stream_resource_lifecycle.test.ts tests/api/studio_proposals_stream_service.test.ts
```

Result: 4 files and 18 tests passed. The cases cover one write per frame,
pull suspension until drain, independent 30-second drain expiry, exact
first-cause retention, normal finish/close, late-event suppression,
primary-first cleanup aggregation, pre-terminal zero persistence, and
post-terminal job/ledger preservation.

The final frontend candidate passed 14 directly affected stream, audit,
identity, whole-book, action-gate, and control-surface files with 97 tests.
The full frontend suite later passed as recorded below. TDD first reproduced
unknown protocol frames being ignored, an A-to-B-to-A audit stuck forever,
terminal frames being overwritten by trailing malformed data, missing focus
return, and a concurrent old whole-book run accepting after a newer audit.
The final monotonic audit epoch invalidates old runs even after a successful
audit notice is explicitly cleared.

Independent server review reported no P0-P3 finding. Independent frontend
review found the protocol, project-identity, focus, and cross-run audit races;
after repair it reported no remaining P0-P3 finding and independently passed
9 focused files with 60 tests. Agent review is supporting evidence, not CI,
release approval, or human acceptance.

## Local full evidence

All successful commands below ran against the final committed tree at
`0cac0b5033152fb9237eedff7dc93f65d6f2c37d`.

| Command | Result |
|---|---|
| `pnpm --dir server test` | Passed in an exclusive rerun: 131 files and 973 tests in 258.52 seconds. |
| `pnpm --dir server gates` | Passed; SSOT, hygiene, migration channel, 468-file size budget, 19 llms-txt links, and OpenAPI snapshot 1/1 were clean. |
| `pnpm --dir server type-check` | Passed. |
| `pnpm --dir server lint` | Passed; 322 files checked with no fixes. |
| `pnpm --dir server arch` | Passed; 187 modules and 774 dependencies had no violation. |
| `pnpm --dir server build` | Passed. |
| `pnpm --dir frontend test:unit` | Passed; 62 files and 325 tests in 31.03 seconds. |
| `pnpm --dir frontend lint` | Passed; 172 files checked with no fixes. |
| `pnpm --dir frontend format:check` | Passed; 171 files checked with no fixes. |
| `pnpm --dir frontend type-check` | Passed. |
| `pnpm --dir frontend build` | Passed; 1,911 modules built and Novel Engine 0.6.0 identity verified in HTML and 7 JavaScript bundles. |
| `pnpm spec:validate` | Passed in strict mode; five active changes plus the canonical specification, 6 of 6 items. |

The first server-full run shared the machine with frontend, build, and gate
processes. Two bcrypt-backed auth rate-limit tests hit their unchanged
10-second test deadlines; the run ended with 971 passed and 2 timed out. No
test or timeout was changed. The affected file then passed alone, 7 of 7 in
17.87 seconds, and the full server suite passed when rerun without competing
validation processes. This resource-contention failure remains recorded rather
than being presented as an initial green run.

## Archive status

This completed change remains **active and not archived**. Required CI has not
run on the integration candidate. Owner: repository maintainer. Closure: every
live required check passes on the exact integration SHA, then archive this
change and rerun canonical-only strict validation.

## External and human gates

- Browser/Playwright workflows: **not run** in this change-local validation.
  Unit tests cover focus restoration and action gating, but they do not replace
  a real browser slow-consumer, navigation, or assistive-technology pass.
  Owner: integrator. Closure: the final repository validation wave runs the
  Playwright workflows against the TypeScript backend and records results.
- Reverse proxy and target-network slow-consumer behavior: **not run**. The
  writer is covered at the Node response boundary, but proxy buffering and
  target deployment timeouts remain external. Owner: deployment maintainer.
  Closure: target proxy/container checks confirm streaming and disconnect
  behavior without weakening the 30-second downstream safety policy.
- GitHub required checks: **not run** because this task did not push or open a
  pull request. Owner: repository maintainer. Closure: every live required
  context is green on the exact integration SHA.
- Human acceptance and accessibility review: **not run** and not implied by
  automated focus tests or agent consensus. Owner: product/release maintainer.
  Closure: an author validates the unknown-outcome warning, audit-only retry,
  explicit “Generate another proposal” action, keyboard focus, and whole-book
  stop/resume behavior in the supported browser.
