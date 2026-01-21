# ci-parity Specification

## Purpose
TBD - created by archiving change add-ci-parity-runner. Update Purpose after archive.
## Requirements
### Requirement: Unified CI Entry Script
The repository MUST expose a single bash entrypoint (`tools/ci/run-all.sh`) that runs every stage (install, lint/typecheck, unit, optional integration/e2e, build) for both GitHub Actions and local developers, with environment toggles to skip heavy suites.

#### Scenario: Local fast pass
- **GIVEN** a developer sets `RUN_INTEGRATION=false` and runs `bash tools/ci/run-all.sh`
- **WHEN** the script executes on their workstation
- **THEN** it installs all declared dependencies (Python/Node/Gradle), runs lint/typecheck/unit stages, clearly logs the skipped integration suite, and exits 0 on success or non-zero on failure.

#### Scenario: GitHub workflow reuse
- **GIVEN** `.github/workflows/ci.yml` needs to run the same checks
- **WHEN** the workflow executes `bash tools/ci/run-all.sh` without overriding `RUN_INTEGRATION`
- **THEN** the integration/docker stages run, artefacts are produced in the same locations as local runs, and any failure bubbles up as a failing GitHub job.

### Requirement: Runner Container and Make Targets
A container image (`devops/runner.Dockerfile`) and `Makefile` targets MUST allow developers to run the CI script inside an environment that mirrors `ubuntu-latest`, including Docker CLI access for service containers.

#### Scenario: make ci builds and runs runner
- **GIVEN** Docker is available locally
- **WHEN** the developer runs `make ci`
- **THEN** the `local-runner` image is built (if needed), the repo is mounted into `/workspace`, the host Docker socket is shared, and the container executes `bash tools/ci/run-all.sh`, producing the same logs/results as GitHub.

#### Scenario: make fast skips container but still uses script
- **GIVEN** a developer wants quick feedback without integration suites
- **WHEN** they run `make fast`
- **THEN** the target exports `RUN_INTEGRATION=false` (and other perf flags), calls the script on the host, and exits non-zero if any stage fails, blocking accidental pushes.

### Requirement: CI Parity Helper Tooling
The repository MUST ship supporting tooling that keeps local state in sync with CI: an integration `docker-compose.ci.yml`, a matrix runner script, and a pre-push hook template documented for adoption.

#### Scenario: Integration stack parity
- **GIVEN** integration tests require Postgres/Redis
- **WHEN** `RUN_INTEGRATION=true` and the script invokes `docker compose -f docker/docker-compose.ci.yml up -d --wait`
- **THEN** the defined services start with health checks, tests run against them, and they are torn down via `docker compose down -v` after the suite finishes.

#### Scenario: Local matrix script
- **GIVEN** the project supports multiple Node/Java/Python versions in CI
- **WHEN** a developer runs `tools/ci/matrix-local.sh`
- **THEN** the script iterates through the configured version tuples inside the runner container, sets `RUN_INTEGRATION=false` by default, and surfaces failures per tuple.

#### Scenario: Pre-push safety net
- **GIVEN** the repository provides `tools/git-hooks/pre-push`
- **WHEN** the hook is symlinked into `.git/hooks/pre-push` and a developer runs `git push`
- **THEN** the hook sources `.env.ci.local` (if present), runs `RUN_INTEGRATION=false bash tools/ci/run-all.sh`, and aborts the push if the script exits non-zero, printing instructions for rerunning.

### Requirement: E2E Test API Health Verification
E2E tests MUST verify that the API server is fully healthy before executing tests, with clear failure messages when the server fails to start.

#### Scenario: API health check rejects partial startup
- **GIVEN** the E2E test suite starts and attempts to verify API readiness
- **WHEN** the API returns HTTP 503 (Service Unavailable) or any non-200 status
- **THEN** the health check MUST NOT consider this successful, MUST continue retrying until timeout, and MUST fail with a clear error message indicating the actual status code received

#### Scenario: API health check validates response body
- **GIVEN** the E2E test suite receives HTTP 200 from the health endpoint
- **WHEN** the response body does not contain `"service_status": "healthy"`
- **THEN** the health check MUST fail with an error message showing the actual service status

#### Scenario: CI workflow has complete Python environment
- **GIVEN** the E2E test workflow runs in GitHub Actions
- **WHEN** the workflow installs dependencies
- **THEN** it MUST set PYTHONPATH to include both project root and src/, install the project in editable mode (`pip install -e .`), and install test requirements from `requirements/requirements-test.txt`

