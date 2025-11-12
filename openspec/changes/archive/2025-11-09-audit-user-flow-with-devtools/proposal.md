## Why
- Need systematic UX/performance audit through Chrome DevTools to validate user interaction flows.
- Current manual testing lacks consistency and doesn't capture performance metrics, accessibility issues, or real-world user scenarios.
- Running frontend and backend processes blocks the terminal, preventing DevTools automation and audit execution.
- Process management gaps:
  - No standardized way to run services in background during development.
  - Lack of health checks and status monitoring for long-running processes.
  - Difficult to coordinate multi-service startup for integration testing.

## What Changes
- Implement process management infrastructure supporting multiple daemon modes (tmux, nohup, PM2, systemd user services, Docker Compose detached).
- Create Chrome DevTools audit workflow to simulate real user interactions (login, dashboard navigation, API calls).
- Add health check endpoints and readiness probes to ensure services are fully operational before running audits.
- Provide automated scripts to start/stop background services and execute comprehensive DevTools audits.

## Success Criteria
- Backend and frontend can be started as background processes using at least 3 different methods (tmux, PM2, Docker Compose).
- Health check endpoints return 200 OK when services are ready to accept traffic.
- Chrome DevTools audit script successfully:
  - Navigates to login page and authenticates
  - Accesses dashboard and triggers key user interactions
  - Captures performance metrics (LCP, FID, CLS)
  - Reports accessibility violations
  - Validates API connectivity and error handling
- Audit report is generated in machine-readable format (JSON) and human-readable format (HTML).
- Process cleanup script properly terminates all background services without leaving orphaned processes.
