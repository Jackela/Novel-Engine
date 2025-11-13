## ADDED Requirements
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
