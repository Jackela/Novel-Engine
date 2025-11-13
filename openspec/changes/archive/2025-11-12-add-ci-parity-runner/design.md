# Design: CI Parity Runner

## Goals
- Run the exact same commands locally and in GitHub Actions without relying on `act`.
- Provide an opt-in containerized environment that mirrors `ubuntu-latest` tooling (Python, Node, Java, Docker) so developers can execute CI scripts deterministically.
- Capture integration dependencies (databases, caches) and version matrices so parity issues surface before merging.

## Key Components
1. **`tools/ci/run-all.sh`**
   - Bash script with `set -euo pipefail` enforcing fast failure.
   - Defines environment switches (`RUN_INTEGRATION`, `RUN_E2E`, `RUN_SLOW`) so workflows can toggle heavy suites.
   - Stages: install (Python/Node/Gradle), lint/typecheck, unit tests, optional integration/e2e via `docker compose -f docker/docker-compose.ci.yml`, and build packaging.
   - Emits section headers for easier parsing in GitHub logs and returns non-zero on first failure.

2. **Runner Container & Make Targets**
   - `devops/runner.Dockerfile` inherits from `ubuntu:24.04`, installs build-essential, Python 3.11/3.12, OpenJDK 21, Node LTS, pnpm/yarn, Docker CLI + compose plugin.
   - `make fast` runs script directly (with `RUN_INTEGRATION=false`), `make ci` builds the `local-runner` image and invokes the script inside, mounting the repo and Docker socket for nested Compose usage.

3. **Parity Helpers**
   - `docker/docker-compose.ci.yml` defines services (Postgres, Redis, etc.) with healthchecks and deterministic credentials for integration suites.
   - `tools/ci/matrix-local.sh` loops through language versions by shelling into the runner container, allowing devs to run `RUN_INTEGRATION=false` smoke passes across the same matrix defined in GitHub.
   - Pre-push hook template sources `.env.ci.local`, enforces a fast run of the script, and prevents pushes on failure.
   - Documentation covers caching, artifact directories, DRY_RUN toggles for publish steps, and instructions for `.env.ci.local` vs GitHub Secrets.

## Workflow Integration
- GitHub workflows collapse to a minimal set of steps: checkout, set up required caches, and `bash tools/ci/run-all.sh` (with matrix variables exported environment-style).
- Developers either call `make fast` (host OS) or `make ci` (container) to replicate the same behaviour.

## Alternatives Considered
- **`act`**: rejected due to partial GitHub feature coverage and slower iteration when workflows use service containers.
- **Duplicating scripts per language**: increases drift; single entrypoint ensures parity.

## Risks / Follow-ups
- Runner image upkeep as GitHub bumps `ubuntu-latest`; mitigate by pinning versions and documenting upgrade steps.
- Docker-in-Docker security/performance; we mount host socket to avoid nested daemon overhead.
