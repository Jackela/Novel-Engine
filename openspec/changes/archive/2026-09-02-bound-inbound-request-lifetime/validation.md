# Validation evidence

## Fixed points

- Comparison SHA: `bf3e010823ceb02c1445b9e623f48d284438dd51`
- Implementation SHA: `d6d4b03e2b65436bf003c5450676f77bd634a89f`
- Final local code candidate SHA: `d6d4b03e2b65436bf003c5450676f77bd634a89f`
- Environment: Darwin 27.0.0 arm64, Node.js 24.19.0, pnpm 11.6.0

## Targeted evidence

Command on the committed code candidate:

```text
pnpm --dir server exec vitest run tests/apps/api/inbound_request_lifetime.test.ts tests/api/project_deletion_proposal_lifecycle.test.ts
```

Result: passed, 2 files and 13 tests in 9.70 seconds. The real-socket cases
prove partial headers receive Node's 408 before Fastify, partial declared
bodies reach only `onRequest`/`preParsing`, undeclared body framing receives a
stable 422 envelope and connection close before its handler, complete long
handlers and delayed SSE frames outlive receipt deadlines, and the 1 MiB body
limit remains enforced. The project-deletion case confirms the bodyless retry
contract still reaches the established project-exclusive 409.

TDD first observed `requestTimeout` at zero, an undeclared body reaching its
handler with 200, and the partial parser later producing 408. The first full
run also exposed one test-helper-only `{}` body on the retry route; tracing all
product callers proved the route is bodyless, so that finding-required test
fixture now sends no body rather than weakening the transport policy.

Independent implementation review reported no P0-P3 finding. It reran the
focused behavior, repeated the raw-socket suite five times, and independently
passed type, lint, architecture, OpenAPI, strict OpenSpec, and diff checks.
Agent review is supporting evidence, not a release or human-acceptance gate.

## Local full evidence

| Command | Result |
|---|---|
| `pnpm --dir server test` | Passed on implementation SHA; 130 files and 960 tests in 255.93 seconds. |
| `pnpm --dir server gates` | Passed; SSOT, hygiene, file-size, migration-channel, llms-txt, and OpenAPI gates were clean across 457 checked files and 19 link targets; OpenAPI snapshot 1/1 passed. |
| `pnpm --dir server type-check` | Passed. |
| `pnpm --dir server lint` | Passed; 320 files checked with no fixes. |
| `pnpm --dir server arch` | Passed; 185 modules and 772 dependencies had no violation. |
| `pnpm --dir server build` | Passed. |
| `pnpm spec:validate -- --strict` | Passed; all four active changes and the canonical specification, 5 of 5 items. |

## Archive status

This completed change remains **active and not archived**. Required CI has not
run on the integration candidate. Owner: repository maintainer. Closure: all
live required checks pass on the exact integration SHA, then archive this
change and rerun canonical-only strict validation.

## External and human gates

- Frontend validation: **not run** for this server transport-policy change.
  Existing product callers send bodies only to routes with declared schemas,
  and server integration coverage exercises the affected HTTP contract.
  Residual risk is a stale or third-party client sending an undeclared body;
  the intentional result is the documented 422. Owner: integrator. Closure:
  the final cross-project validation wave runs the frontend suite.
- Reverse-proxy/container validation: **not run** locally. Raw Node sockets
  cover the application server, but an edge proxy may enforce a shorter
  request-receipt policy first. Owner: repository CI/deployment maintainer.
  Closure: container and target-proxy checks pass without weakening the server
  thresholds.
- GitHub required checks: **not run** because this task did not push or open a
  pull request. Residual risk is Linux/CI-only timing and live branch-protection
  checks. Owner: repository maintainer. Closure: every live required context is
  green on the exact integration SHA.
- Human acceptance: **not run** and not implied by socket tests or agent review.
  Residual risk is operator acceptance of 60/120-second receipt thresholds in
  the deployment topology. Owner: deployment/release maintainer. Closure: the
  owner records explicit acceptance if required for release.
