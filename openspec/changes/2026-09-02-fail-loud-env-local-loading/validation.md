# Validation evidence

## Fixed points

- Comparison SHA: `a7be8ac960acbed8d099e4e31eef711206a87c85`
- Implementation SHA: `ed7ec04c2e4f8c5b21e4dcd85f4f78282b9808ff`
- Final local code candidate SHA: `ed7ec04c2e4f8c5b21e4dcd85f4f78282b9808ff`
- Environment: Darwin 27.0.0 arm64, Node.js 24.19.0, pnpm 11.6.0

## Targeted evidence

Command on the clean fixed-SHA candidate:

```text
pnpm --dir server exec vitest run tests/infrastructure/server_config.test.ts tests/infrastructure/server_config_env_file_failures.test.ts tests/apps/cli/cli.test.ts tests/apps/cli/cli_database_authority.test.ts tests/apps/cli/cli_lifecycle.test.ts tests/apps/cli/cli_env_file_failures.test.ts tests/apps/cli/cli_shutdown_signals.test.ts tests/apps/cli/shutdown_signals.test.ts
```

Result: passed, 8 files and 62 tests. The environment-focused cases prove that
only `ENOENT` is optional; non-regular targets fail consistently; symbolic
links to regular files work; actual metadata/read errors and parser exceptions
retain object identity; process values cannot mask failure; and serve, backup,
import, and doctor stop before their downstream side effects.

TDD first reproduced swallowed directory, read, and parser failures. A
cross-platform review then exposed Node's platform-specific directory-read
behavior; regular-file validation and symlink coverage failed before the
portable fix and passed afterward.

Independent specification, code, and integration reviews reported no remaining
P0-P3 finding. Agent review is supporting evidence, not a release gate.

## Local full evidence

| Command | Result |
|---|---|
| `pnpm --dir server test` | Passed on the clean fixed-SHA candidate; 128 files and 947 tests in 305.50 seconds. |
| `pnpm --dir server gates` | Passed; SSOT, hygiene, file-size, migration-channel, llms-txt, and OpenAPI gates were clean across 452 checked files. |
| `pnpm --dir server type-check && pnpm --dir server lint && pnpm --dir server arch && pnpm --dir server build` | Passed; 315 files passed Biome and 183 modules / 764 dependencies had no architecture violation. |
| `pnpm spec:validate` | Passed in strict mode for both active changes and the canonical specification, 3 of 3 items. |

## External and human gates

- Frontend validation: **not applicable** to this change's local-full surface
  because neither frontend source nor the HTTP schema changed. Residual risk:
  none introduced on the frontend by this write set. Owner: integrator.
  Closure: rerun the frontend surfaces if later integration changes either
  frontend code or the HTTP contract.
- Docker validation: **not run** because the local host has no Docker
  executable. Residual risk is container-host filesystem and signal behavior.
  Owner: repository CI. Closure: the container job passes on the integration
  SHA.
- GitHub required checks: **not run** because this task did not push or open a
  pull request. Residual risk is Linux/CI-only behavior, live branch-protection
  requirements, and checks not represented by local scripts. Owner: repository
  maintainer. Closure: all live required checks are green on the exact
  integration SHA.
- Human acceptance: **not run** because this local implementation task is not a
  release-approval session; it is not required for local candidate closure but
  is required before any status that claims release approval. Residual risk is
  operator acceptance of fail-fast startup behavior in the target deployment.
  Owner: release maintainer. Closure: the owner performs and records explicit
  release acceptance if the target release requires it.
