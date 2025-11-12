## Why
- GitHub workflows (e.g., `.github/workflows/ci.yml`) currently run inline shell steps; there is no shared script for installations, linting, unit, integration, or build stages, so developers cannot easily reproduce CI locally.
- Engineers asked for a “绕开 act”的 solution that mirrors the GitHub runner environment by dropping commands into a reusable script and executing it inside a runner-like container. The repo does not yet provide `tools/ci/run-all.sh`, a Docker runner image, or helper tooling described in the request.
- Integration tests depend on services such as Postgres/Redis but there is no dedicated `docker-compose.ci.yml`, matrix runner, or pre-push safety net to guarantee parity before opening a PR.

## What Changes
- Introduce a single entrypoint script (`tools/ci/run-all.sh`) that installs dependencies, runs lint/typecheck/unit/integration steps, supports `RUN_INTEGRATION`/`RUN_E2E` toggles, and becomes the command GitHub Actions executes.
- Provide a `devops/runner.Dockerfile` plus Make targets so developers can run the same script inside a container that approximates `ubuntu-latest`, with optional local matrix execution (`tools/ci/matrix-local.sh`).
- Add CI support artifacts: `docker-compose.ci.yml` for integration dependencies, docs for `.env.ci.local` secrets, a pre-push hook template invoking the script, and guidance for caching/artifacts/dry-run behaviour.

## Impact
- **Developers** get deterministic, locally reproducible CI runs without relying on `act` or bespoke runner setups.
- **CI pipelines** simplify to `bash tools/ci/run-all.sh`, reducing drift between workflows and scripting logic.
- **Quality gates** catch parity issues earlier because integration stacks, matrices, and hooks run the same entrypoint before code reaches GitHub.
