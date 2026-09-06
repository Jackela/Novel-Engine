# Validation evidence

## Fixed points

- Comparison SHA: `a7be8ac960acbed8d099e4e31eef711206a87c85`
- Implementation SHA: `f6e47d040f96b30d22cc861f989cb48bea393c85`
- Final local candidate SHA: `edf77e6aaa473f6fa1cdce8e0bb19b22bd14d5d9`
- Environment: Darwin 27.0.0 arm64, Node.js 24.19.0, pnpm 11.6.0

## Targeted evidence

Command on the clean fixed-SHA candidate:

```text
pnpm --dir server exec vitest run tests/infrastructure/server_config.test.ts tests/infrastructure/server_config_env_file_failures.test.ts tests/apps/cli/cli.test.ts tests/apps/cli/cli_database_authority.test.ts tests/apps/cli/cli_lifecycle.test.ts tests/apps/cli/cli_env_file_failures.test.ts tests/apps/cli/cli_shutdown_signals.test.ts tests/apps/cli/shutdown_signals.test.ts
```

Result: passed, 8 files and 62 tests. The shutdown-focused cases cover the
pre-invocation lifecycle discriminator, pre-listen registration, startup-time
signals, first-cause ownership, repeated signals during delayed cleanup,
exact/idempotent removal, partial-registration rollback, runner-owned success
and failure, cleanup aggregation, and statuses 130, 143, and 1.

TDD first produced 12 expected failures against the old void runner and absent
latch. Independent review found one slow-listener-cleanup signal window and one
test gate leak; both were reproduced, fixed, and re-reviewed with no remaining
P0-P3 finding.

An independent emitted-process smoke built the exact final code SHA, selected
an ephemeral loopback port, waited for `Server listening`, sent `SIGTERM`, and
observed:

```json
{"sha":"edf77e6aaa473f6fa1cdce8e0bb19b22bd14d5d9","ready":true,"requestedSignal":"SIGTERM","code":143,"signal":null,"databaseCreated":true,"logObserved":true}
```

The null terminating signal confirms the CLI handled the signal, completed its
controlled close, and returned status 143 rather than being killed directly.
Agent review and this smoke are supporting evidence, not release approval.

## Local full evidence

| Command | Result |
|---|---|
| `pnpm --dir server test` | Passed on the clean final local candidate; 128 files and 947 tests in 193.99 seconds. |
| `pnpm --dir server gates` | Passed; SSOT, hygiene, file-size, migration-channel, llms-txt, and OpenAPI gates were clean across 453 checked files. |
| `pnpm --dir server type-check && pnpm --dir server lint && pnpm --dir server arch && pnpm --dir server build` | Passed; 316 files passed Biome and 183 modules / 764 dependencies had no architecture violation. |
| `pnpm spec:validate` | Passed in strict mode for both active changes and the canonical specification, 3 of 3 items. |

## Archive status

This completed change remains **active and not archived**. A local archive
attempt (`22e53511ecb610ee8fe779add87010b02186ccb6`) was reversed by
`e898503f` and `3896f9ae` after final review enforced the repository rule that
archiving occurs only after CI is green. During that abandoned dirty-tree move,
`gate:hygiene` also tried to read a deleted active path and raised `ENOENT`; the
post-commit gate passed, and the shared candidate-file enumeration defect is a
separate tooling finding. Owner: repository maintainer. Closure: required CI is
green on the exact integration SHA, then the active change is archived and the
canonical-only strict gate passes.

## External and human gates

- Frontend validation: **not applicable** to this change's local-full surface
  because neither frontend source nor the HTTP schema changed. Residual risk:
  none introduced on the frontend by this write set. Owner: integrator.
  Closure: rerun the frontend surfaces if later integration changes either
  frontend code or the HTTP contract.
- Docker validation: **not run** because the local host has no Docker
  executable. Residual risk is container init/signal forwarding and active
  stream draining. Owner: repository CI. Closure: the container job passes on
  the integration SHA.
- Bounded active-stream drain and second-signal escalation: **not implemented or
  claimed** by this change. Residual risk is that active streams can delay
  process completion without a finite bound. Owner: a separate resource-drain
  finding. Closure: an independently specified drain/timeout policy is
  implemented and validated.
- GitHub required checks: **not run** because this task did not push or open a
  pull request. Residual risk is Linux/CI-only signal behavior, live
  branch-protection requirements, and checks not represented by local scripts.
  Owner: repository maintainer. Closure: all live required checks are green on
  the exact integration SHA.
- Human acceptance: **not run** because this local implementation task is not a
  release-approval session; it is not required for local candidate closure but
  is required before any status that claims release approval. Residual risk is
  operator acceptance of shutdown behavior under the target process supervisor.
  Owner: release maintainer. Closure: the owner performs and records explicit
  release acceptance if the target release requires it.
