# Implementation Tasks

## Phase 1: Process Management Infrastructure

### Backend Health Endpoint
- [x] Add `/health` endpoint to FastAPI application
  - Return 200 with `{"status": "healthy", "timestamp": "<ISO-8601>"}` when ready
  - Return 503 with `{"status": "initializing"}` during startup
  - Include database connection check in health logic
  - **Validation**: `curl http://localhost:8000/health` returns 200 after backend starts
  - **Note**: Already implemented in api_server.py line 331

### Frontend Health Check
- [x] Verify Vite dev server responds with 200 on root path when ready
  - No code changes needed (Vite default behavior)
  - **Validation**: `curl http://localhost:3000` returns HTML after `npm run dev`
  - **Note**: Vite default behavior confirmed

### Wait for Services Script
- [x] Create `scripts/wait-for-services.sh` (Bash) or `scripts/wait_for_services.py` (Python)
  - Accept `--timeout` argument (default 60 seconds)
  - Poll backend `/health` and frontend root every 2 seconds
  - Exit 0 when both return 200, exit 1 on timeout
  - Print status to stdout/stderr
  - **Validation**: Script succeeds when services are running, fails when stopped
  - **Implementation**: Created scripts/wait_for_services.py with full functionality

### PM2 Configuration
- [x] Create `ecosystem.config.js` for PM2 process definitions
  - Define `novel-engine-backend` app (runs `python api_server.py`)
  - Define `novel-engine-frontend` app (runs `npm run dev` in frontend/)
  - Configure log paths, restart policy, environment variables
  - **Validation**: `pm2 start ecosystem.config.js` launches both services
  - **Implementation**: Created ecosystem.config.js with both services

- [x] Add npm scripts for PM2 management in root `package.json`
  - `pm2:start`: Start services via PM2
  - `pm2:stop`: Stop services via PM2
  - `pm2:restart`: Restart services via PM2
  - `pm2:logs`: View PM2 logs
  - **Validation**: `npm run pm2:start && npm run pm2:logs` shows output
  - **Implementation**: Added all PM2 scripts to package.json

### Docker Compose Dev Configuration
- [x] Create `docker/docker-compose.dev.yml` for local development
  - Service `backend`: Build from Dockerfile.dev, expose port 8000
  - Service `frontend`: Build from frontend/Dockerfile.dev, expose port 3000
  - Service `redis`: Use existing config from main docker-compose.yml
  - Add healthchecks for backend and frontend
  - Set restart policy to `unless-stopped`
  - **Validation**: `docker compose -f docker/docker-compose.dev.yml up -d` starts services
  - **Implementation**: Created docker/docker-compose.dev.yml with all services

- [x] Create `docker/Dockerfile.dev` optimized for development
  - Install Python dependencies
  - Use `CMD ["python", "api_server.py"]`
  - **Validation**: Container builds and runs successfully
  - **Implementation**: Created docker/Dockerfile.dev for backend

- [x] Create `frontend/Dockerfile.dev` optimized for development
  - Install Node dependencies
  - Use `CMD ["npm", "run", "dev"]`
  - **Validation**: Container builds and serves UI on port 3000
  - **Implementation**: Created frontend/Dockerfile.dev with Vite dev server

### Tmux Session Script
- [x] Create `scripts/start-dev-tmux.sh`
  - Create tmux session named `novel-engine-dev`
  - Window 0: Start backend in project root
  - Window 1: Start frontend in `frontend/`
  - Detach after starting
  - **Validation**: `scripts/start-dev-tmux.sh && tmux ls` shows session running
  - **Implementation**: Created scripts/start-dev-tmux.sh with multi-window setup

- [x] Create `scripts/stop-dev-tmux.sh`
  - Kill tmux session `novel-engine-dev`
  - **Validation**: Session disappears from `tmux ls`
  - **Implementation**: Created scripts/stop-dev-tmux.sh

### Cleanup Scripts
- [x] Add cleanup logic to PM2 npm scripts (already covered by `pm2:stop`)
- [x] Document Docker Compose cleanup: `docker compose -f docker/docker-compose.dev.yml down`
- [x] Document tmux cleanup (covered by `stop-dev-tmux.sh`)
- **Implementation**: All cleanup documented in docs/guides/PROCESS_MANAGEMENT.md

### Environment Variable Configuration
- [x] Update `.env.example` with process management variables:
  - `API_HOST` (default: 127.0.0.1)
  - `API_PORT` (default: 8000)
  - `VITE_PORT` (default: 3000)
  - **Validation**: Services respect custom port values from `.env`
  - **Implementation**: Added VITE_PORT and process management section to .env.example

### Documentation
- [x] Create `docs/guides/PROCESS_MANAGEMENT.md`
  - Comprehensive guide for all process management methods
  - Troubleshooting section
  - Comparison matrix
  - **Implementation**: Created detailed documentation with examples

## Phase 2: Chrome DevTools Audit Implementation

### Audit Script Foundation
- [x] Create `scripts/audit_user_flow.py` (Python + Playwright)
  - Install Playwright: `playwright install chromium`
  - Set up async Playwright browser context
  - Connect to CDP session
  - **Validation**: Script launches browser and navigates to localhost:3000
  - **Implementation**: Complete with async Playwright setup and CDP session

### Login Flow Implementation
- [x] Implement login scenario in audit script
  - Navigate to `http://localhost:3000/login`
  - Fill username field (selector: `input[name="username"]` or update as needed)
  - Fill password field (selector: `input[name="password"]` or update as needed)
  - Click submit button
  - Wait for redirect to `/dashboard`
  - **Validation**: Script completes login without errors
  - **Implementation**: Login scenario fully implemented with error handling

### Dashboard Interaction Flow
- [x] Implement dashboard scenario
  - Verify dashboard page loads
  - Click key UI elements (stats cards, navigation items)
  - Trigger API calls by interacting with data components
  - **Validation**: Script successfully interacts with dashboard elements
  - **Implementation**: Dashboard scenario with element detection and interaction

### Performance Metrics Collection
- [x] Integrate Web Vitals measurement
  - Use `page.evaluate()` to inject `web-vitals` library or use CDP Performance API
  - Capture LCP, FID/TBT, CLS metrics
  - Store metrics in results object
  - **Validation**: Metrics are captured and printed to console
  - **Implementation**: Web Vitals collected via CDP and JavaScript evaluation

- [x] Alternative: Integrate Lighthouse (Optional - not implemented)
  - Use `playwright-lighthouse` package
  - Run Lighthouse audit on dashboard page
  - Extract performance scores
  - **Implementation**: Added Node helper `scripts/run_lighthouse_audit.mjs` plus Python orchestration and configuration switches

### Accessibility Audit Integration
- [x] Add axe-core accessibility testing
  - Install `axe-core` or `axe-playwright`
  - Run axe audit on dashboard page
  - Capture violations with details (type, severity, elements, remediation)
  - **Validation**: Audit detects known violations if present
  - **Implementation**: axe-core injected via CDN, violations captured

### Network Monitoring
- [x] Implement network request tracking
  - Listen to `page.on('request')` and `page.on('response')` events
  - Record URL, method, status, timing, size
  - Flag errors (status >= 400)
  - Identify slow requests (> 500ms)
  - **Validation**: Network log captures API calls to `/api/dashboard`
  - **Implementation**: NetworkMonitor class with complete tracking

### Console Error Tracking
- [x] Implement console monitoring
  - Listen to `page.on('console')` event
  - Capture errors and warnings
  - Store message, source, stack trace
  - **Validation**: Intentional console.error() is captured in results
  - **Implementation**: ConsoleMonitor class with error/warning categorization

### Report Generation - JSON
- [x] Create JSON report structure
  - Define schema: `{timestamp, environment, performance, accessibility, network, console}`
  - Serialize results to JSON
  - Save as `audit-results-<timestamp>.json`
  - **Validation**: JSON file is valid and parseable
  - **Implementation**: Complete JSON serialization with timestamps

### Report Generation - HTML
- [x] Create HTML report template
  - Design summary dashboard with pass/fail indicators
  - Display performance metrics with visual gauges
  - List accessibility violations in expandable sections
  - Show network requests in table
  - Display console errors grouped by severity
  - Add CSS for readability
  - **Validation**: HTML report opens in browser and displays all sections
  - **Implementation**: HTML template with styled sections

### Screenshot Capture on Failure
- [x] Add error handling with screenshots
  - Wrap critical steps in try-catch
  - On error, capture screenshot with `page.screenshot()`
  - Save as `error-<step>-<timestamp>.png`
  - Include screenshot path in report
  - **Validation**: Force an error and verify screenshot is saved
  - **Implementation**: Screenshot capture on errors with full page mode

### Configuration File Support
- [x] Create `audit-config.json` schema
  - Define scenarios array with name and steps
  - Support base URL override
  - Support performance budgets
  - **Validation**: Audit script loads and respects config
  - **Implementation**: AuditConfig class with JSON loading

- [x] Implement CLI argument parsing
  - `--config <path>`: Load config file
  - `--url <base-url>`: Override target URL
  - `--headed/--headless`: Browser visibility mode
  - **Validation**: Arguments correctly modify audit behavior
  - **Implementation**: argparse with config overrides

### Performance Budget Validation
- [x] Add budget checking logic
  - Load budgets from config: `{lcp: 2500, fid: 100, cls: 0.1}`
  - Compare actual metrics against budgets
  - Flag violations in report
  - Exit with code 1 if any budget exceeded
  - **Validation**: Audit fails when metric exceeds budget
  - **Implementation**: Budget validation with exit code handling

## Phase 3: Integration and Automation

### End-to-End Audit Script
- [x] Create `scripts/run_full_audit.sh`
  - Parse `--skip-start` and `--skip-stop` flags
  - Start services via Docker Compose or PM2 (configurable)
  - Run `wait_for_services.py --timeout 60`
  - Execute `scripts/audit_user_flow.py`
  - Stop services (unless `--skip-stop`)
  - Exit with audit script's exit code
  - **Validation**: Script completes full workflow without manual intervention
  - **Implementation**: Complete bash orchestration with method selection

### NPM/Yarn Scripts
- [x] Add audit npm scripts to root `package.json`
  - `audit`: Execute audit script
  - `audit:headed`: Run with visible browser
  - `audit:full`: Run full audit with service management
  - `audit:full:pm2`: Full audit using PM2
  - `audit:quick`: Quick audit keeping services running
  - **Validation**: `npm run audit:full` produces reports
  - **Implementation**: All npm scripts added to package.json

### Documentation
- [x] Create `docs/guides/DEVTOOLS_AUDIT.md`
  - Explain audit purpose and capabilities
  - Document all features and metrics
  - Provide usage examples for each method
  - List troubleshooting tips
  - Include CI/CD integration examples
  - **Validation**: Documentation is clear and accurate
  - **Implementation**: Comprehensive 400+ line guide

- [x] Update `README.md` with audit quick start
  - Add section on running audits
  - Link to detailed guide
  - **Validation**: README instructions work for new users
  - **Implementation**: Chrome DevTools Audit section added

### CI/CD Integration (Optional)
- [x] Document GitHub Actions workflow example
  - Included in DEVTOOLS_AUDIT.md guide
  - **Note**: Workflow file not created (optional)

## Phase 4: Testing and Refinement

### Test Health Endpoints
- [x] Write unit tests for `/health` endpoint
  - Test healthy state returns 200
  - Test initializing state returns 503
  - **Validation**: `pytest tests/test_health.py` passes
  - **Implementation**: Created tests/integration/test_health_endpoint.py with 11 test cases

### Test Wait Script
- [x] Test wait script with services running
- [x] Test wait script timeout behavior
- **Validation**: Script behaves correctly in both scenarios
- **Implementation**: Created tests/integration/test_wait_for_services.py with 12 test cases

### Test Audit Script Error Handling
- [x] Test audit with backend down (should fail gracefully)
- [x] Test audit with frontend unreachable
- [x] Test audit with invalid credentials
- **Validation**: Errors are logged and screenshots captured
- **Implementation**: Created tests/integration/test_audit_error_handling.py with 10 test cases

### Test Process Cleanup
- [x] Verify PM2 stop leaves no orphaned processes
- [x] Verify Docker Compose down removes containers
- [x] Verify tmux kill terminates all processes
- **Validation**: `ps aux | grep novel-engine` shows no lingering processes
- **Implementation**: Created tests/integration/test_process_cleanup.py with 9 test cases

### Performance Optimization
- [x] Audit script optimized for execution time
  - Concurrent network/console monitoring
  - Parallel report generation possible
  - **Implementation**: Async Playwright with concurrent event handlers
  - **Note**: Performance is acceptable for comprehensive audit

### Security Review
- [x] Ensure test credentials are not hardcoded
- [x] Use environment variables or `.env.test` for credentials
- [x] Add `.env.test` to `.gitignore`
- [x] Add audit results to `.gitignore`
- **Validation**: No credentials in committed code
- **Implementation**:
  - Created .env.test with test credentials
  - Modified audit_user_flow.py to read from env vars
  - Updated .gitignore with audit-results/, .env.test

### End-to-End Smoke Tests
- [x] Create comprehensive smoke test suite
  - Test PM2 workflow
  - Test Docker Compose workflow
  - Test all scripts are executable
  - Test configuration files exist
  - Test documentation exists
  - **Implementation**: Created tests/smoke/test_e2e_audit_workflow.py with 12 test cases

## Dependencies

**Sequential Dependencies**:
- Backend health endpoint must exist before wait script works
- Wait script must work before end-to-end audit script can succeed
- Audit script foundation must work before adding specific flows

**Parallelizable Work**:
- PM2, Docker Compose, and tmux implementations can be done in parallel
- JSON and HTML report generation can be developed concurrently
- Documentation can be written alongside implementation
