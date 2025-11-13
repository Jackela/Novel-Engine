## ADDED Requirements
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
