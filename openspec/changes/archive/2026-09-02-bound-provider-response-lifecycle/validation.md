# Validation evidence

## Fixed points

- Comparison SHA: `329196b86d6c6588f0e8a47228a8d1c996f583f1`
- Implementation SHA: `92fe7a2c335653d8852401dd7b197f7687524fbd`
- Final local candidate SHA: `3c54f7fa025e446a2e521f82c32156d1bab13656`
- Environment: Darwin 27.0.0 arm64, Node.js 24.19.0, pnpm 11.6.0

## Targeted evidence

Command:

```text
pnpm --dir server exec vitest run tests/contexts/dashscope_provider.test.ts tests/contexts/openai_compatible_provider.test.ts tests/contexts/provider_streaming_timeouts.test.ts tests/contexts/provider_response_bounds.test.ts tests/contexts/provider_response_deadline.test.ts tests/contexts/provider_streaming_deadline.test.ts tests/contexts/provider_external_cancellation.test.ts tests/contexts/provider_sse_boundaries.test.ts tests/contexts/provider_proposal_limits.test.ts tests/contexts/provider_response_cleanup_races.test.ts tests/contexts/provider_failure_body.test.ts tests/api/studio_proposals_stream_limits.test.ts tests/api/studio_proposals_stream_service.test.ts
```

Result on the final local candidate: passed, 13 files and 71 tests. This covers
absolute dispatch-to-body deadlines, silence budgets, chapter timeout floors,
bounded synchronous and SSE bodies, per-event limits, mixed line endings,
Unicode code-point proposal limits, first-cause cancellation, failure-body
cleanup, late responses, and programming-error visibility.

Independent read-only reviews examined provider failure taxonomy, cancellation
and cleanup races, streaming parsers, and proposal accounting. Confirmed
findings were reproduced and fixed; the final closure review reported no
remaining P0-P3 finding. Agent review is supporting evidence, not a validation
gate.

Supporting checks on implementation SHA
`92fe7a2c335653d8852401dd7b197f7687524fbd` also exercised 5,000 randomized
Unicode counter cases and 1,000 randomized SSE-boundary cases. They are
historical implementation evidence; the fixed-SHA Vitest command above is the
candidate evidence.

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
  provider lifecycle and resource-bound behavior; browser automation and agent
  review are supporting evidence only. Owner: release maintainer. Closure:
  explicit human release approval if the target release requires it.
