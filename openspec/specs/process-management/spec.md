# process-management Specification

## Purpose
TBD - created by archiving change audit-user-flow-with-devtools. Update Purpose after archive.
## Requirements
### Requirement: Support Multiple Process Management Methods
The system MUST provide scripts to start frontend and backend services as background processes using at least three different methods: PM2, Docker Compose detached mode, and tmux sessions.

#### Scenario: Developer starts services with PM2
```
GIVEN the developer has PM2 installed globally
WHEN they run `npm run pm2:start` from the project root
THEN the backend FastAPI server starts on port 8000
AND the frontend Vite dev server starts on port 3000
AND both processes run in the background without blocking the terminal
AND PM2 logs are accessible via `pm2 logs`
```

#### Scenario: Developer starts services with Docker Compose
```
GIVEN Docker and Docker Compose are installed
WHEN the developer runs `docker compose -f docker/docker-compose.dev.yml up -d`
THEN all services (backend, frontend, redis) start in detached mode
AND the developer can continue using the terminal
AND services are accessible on their configured ports
AND logs can be viewed with `docker compose logs -f`
```

#### Scenario: Developer starts services with tmux
```
GIVEN tmux is installed
WHEN the developer runs `scripts/start-dev-tmux.sh`
THEN a new tmux session named "novel-engine-dev" is created
AND the backend runs in window 0
AND the frontend runs in window 1
AND the developer can attach to the session with `tmux attach -t novel-engine-dev`
AND the developer can detach and keep processes running
```

### Requirement: Health Check Endpoints
The backend MUST expose a `/health` endpoint that returns service readiness status. The frontend MUST respond with HTTP 200 when the Vite dev server is ready.

#### Scenario: Backend health check returns ready status
```
GIVEN the backend server has fully initialized
AND database connections are established
WHEN a client sends GET /health
THEN the response status is 200 OK
AND the response body includes {"status": "healthy", "timestamp": "<ISO-8601>"}
```

#### Scenario: Backend health check returns not ready
```
GIVEN the backend server is still initializing
WHEN a client sends GET /health
THEN the response status is 503 Service Unavailable
AND the response body includes {"status": "initializing"}
```

#### Scenario: Frontend responds when Vite dev server is ready
```
GIVEN the Vite dev server has completed initialization
WHEN a client sends GET http://localhost:3000
THEN the response status is 200 OK
AND the response includes HTML content
```

### Requirement: Service Startup Wait Script
The system MUST provide a script that waits for both frontend and backend services to become healthy before proceeding.

#### Scenario: Wait script succeeds when services are ready
```
GIVEN services are starting in the background
WHEN the developer runs `scripts/wait-for-services.sh --timeout 60`
THEN the script polls /health endpoints every 2 seconds
AND the script exits with code 0 when both services return 200
AND the script prints "Services ready" to stdout
```

#### Scenario: Wait script times out if services don't start
```
GIVEN services fail to start within the timeout period
WHEN the developer runs `scripts/wait-for-services.sh --timeout 10`
THEN the script polls for 10 seconds
AND the script exits with code 1
AND the script prints "Timeout waiting for services" to stderr
```

### Requirement: Service Cleanup Script
The system MUST provide a cleanup script that properly terminates all background processes without leaving orphaned processes.

#### Scenario: Cleanup script stops PM2 processes
```
GIVEN services are running via PM2
WHEN the developer runs `npm run pm2:stop`
THEN all PM2-managed processes for this project are stopped
AND PM2 confirms "stopped 2 processes"
AND no orphaned node/python processes remain
```

#### Scenario: Cleanup script stops Docker Compose services
```
GIVEN services are running via Docker Compose
WHEN the developer runs `docker compose -f docker/docker-compose.dev.yml down`
THEN all containers are stopped and removed
AND networks are cleaned up
AND volumes persist unless --volumes flag is used
```

#### Scenario: Cleanup script kills tmux session
```
GIVEN services are running in tmux session "novel-engine-dev"
WHEN the developer runs `scripts/stop-dev-tmux.sh`
THEN the tmux session is killed
AND all processes in the session are terminated
AND `tmux ls` no longer shows "novel-engine-dev"
```

### Requirement: Configuration for Port and Host Settings
Process management scripts MUST read port and host configuration from environment variables or config files.

#### Scenario: Backend port is configurable
```
GIVEN the environment variable API_PORT=8080 is set
WHEN the backend starts via any process manager
THEN the FastAPI server listens on port 8080
AND the health check is accessible at http://localhost:8080/health
```

#### Scenario: Frontend port is configurable
```
GIVEN the environment variable VITE_PORT=3001 is set
WHEN the frontend starts via any process manager
THEN the Vite dev server listens on port 3001
AND the UI is accessible at http://localhost:3001
```

### Requirement: Process Monitoring and Restart
For PM2 and Docker Compose methods, processes MUST automatically restart on crash.

#### Scenario: PM2 restarts crashed backend
```
GIVEN the backend is running via PM2
WHEN the backend process crashes
THEN PM2 automatically restarts the process within 5 seconds
AND the restart is logged in PM2 logs
AND the health check returns 200 after reinitialization
```

#### Scenario: Docker Compose restarts crashed container
```
GIVEN services are running with restart policy "unless-stopped"
WHEN the backend container crashes
THEN Docker Compose restarts the container
AND the container logs show the restart event
AND the service becomes healthy again
```

### Requirement: Unified Non-blocking Dev Bootstrap Script
The repository MUST provide a documented script that starts backend and frontend services in the background, waits for both health checks, and returns control to the shell.

#### Scenario: Developer launches `scripts/dev_env_daemon.sh`
- **GIVEN** Python and Node dependencies are installed
- **AND** the developer runs `scripts/dev_env_daemon.sh` (or `npm run dev:daemon`) from the repo root
- **THEN** the backend API server starts on the configured port, the frontend Vite dev server starts on its configured port, and logs stream to `tmp/dev_env.log`
- **AND** the script polls `/health` and `http://localhost:<vite>` until both return 200 or timeout, then prints "Backend ready" / "Frontend ready" plus URLs
- **AND** control returns to the shell while both processes continue running in the background, with instructions to stop them via the documented cleanup command

#### Scenario: README documents bootstrap + cleanup flow
- **GIVEN** the README quick-start section is referenced by contributors
- **WHEN** the non-blocking script changes its CLI, ports, or prerequisites
- **THEN** the README (both languages) is updated in the same change to describe the command, ports, health endpoints, and cleanup method so contributors can reproduce the experience without guessing

### Requirement: Guided Dev Environment Bootstrap
Developers MUST have a single `scripts/dev_env.sh` helper that launches the FastAPI (`src.api.main_api_server`) and Vite dev servers simultaneously, streams logs, and terminates both processes when interrupted.

#### Scenario: Script starts both services
- **GIVEN** Python/Node dependencies are installed
- **WHEN** a developer runs `scripts/dev_env.sh start`
- **THEN** the FastAPI server starts on `$API_HOST:$API_PORT`
- **AND** the Vite dev server starts on `$VITE_HOST:$VITE_PORT`
- **AND** the script prints both log streams with clear prefixes

#### Scenario: Script handles cleanup
- **GIVEN** `scripts/dev_env.sh` is running
- **WHEN** the developer presses `Ctrl+C`
- **THEN** the script traps the signal
- **AND** stops both child processes
- **AND** prints "Dev environment stopped cleanly"

### Requirement: AI-Native Playwright Validation
The frontend MUST expose `npm run ai:test` which runs tagged Playwright usability specs (with mocked APIs) and emits trace/video artifacts for downstream AI agents.

#### Scenario: AI test command executes tagged suite
- **GIVEN** the repository dependencies are installed
- **WHEN** a developer runs `npm run ai:test`
- **THEN** Playwright executes only specs tagged `@ai`
- **AND** generates trace/video artifacts in `playwright-report` or `test-results`
- **AND** exits non-zero on any usability regression

#### Scenario: CI parity script calls AI tests
- **GIVEN** `RUN_AI_TESTS` is `true` (default)
- **WHEN** `tools/ci/run-all.sh` runs (locally或在 GitHub Actions)
- **THEN** it invokes `npm run ai:test`
- **AND** the pipeline fails if AI usability specs regress

#### Scenario: One-command CI wrapper
- **GIVEN** a developer or AI assistant runs `scripts/run_ci.sh`
- **THEN** the script exports recommended `RUN_*` environment flags
- **AND** defers to `tools/ci/run-all.sh`
- **SO THAT** local runs mirror GitHub Actions without remembering multiple commands

### Requirement: Playwright smoke vs full pipelines
The CI pipeline MUST provide two Playwright tracks: a <1 minute smoke run for PR validation and the existing full suite for nightly/merge events, ensuring faster feedback while preserving coverage.

#### Scenario: Smoke run for PRs
- **GIVEN** a PR workflow runs `npm run test:e2e:smoke`
- **THEN** it executes a curated subset (CTA + offline tests) and finishes in under 60 seconds.

#### Scenario: Full run for nightly/main
- **GIVEN** the nightly or main-branch workflow
- **WHEN** it runs `npm run test:e2e`
- **THEN** the existing full suite executes, generating the Experience Report and attaching artifacts.

### Requirement: Publish experience summary to CI job output
Playwright jobs MUST append a condensed experience summary (CTA/offline statuses and links to full reports) to the CI job summary so reviewers can see results without downloading artifacts.

#### Scenario: GitHub job summary shows CTA/offline table
- **WHEN** the Playwright workflow completes in CI
- **THEN** `$GITHUB_STEP_SUMMARY` contains a Markdown table with Demo CTA + offline recovery statuses and a link to the HTML/Markdown report artifacts.

### Requirement: Report cleanup in workflows
CI and local workflows that generate experience reports MUST enforce the retention rule (clean up older files) to keep working directories tidy.

#### Scenario: CI run prunes old reports
- **WHEN** the GitHub workflow runs Playwright + report generation
- **THEN** it automatically prunes reports beyond the retention limit before uploading artifacts.

