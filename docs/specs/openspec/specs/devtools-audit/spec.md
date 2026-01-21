# devtools-audit Specification

## Purpose
TBD - created by archiving change audit-user-flow-with-devtools. Update Purpose after archive.
## Requirements
### Requirement: Automated User Flow Audit Script
The system MUST provide a script that uses Chrome DevTools Protocol to simulate real user interactions and capture performance, accessibility, and network metrics.

#### Scenario: Audit script completes login flow
```
GIVEN the backend and frontend are running and healthy
WHEN the audit script executes the login flow
THEN the script navigates to http://localhost:3000/login
AND fills the username field with test credentials
AND fills the password field with test credentials
AND clicks the submit button
AND waits for navigation to /dashboard
AND the script reports success
```

#### Scenario: Audit script captures performance metrics
```
GIVEN the audit script has completed the user flow
WHEN the script collects performance data
THEN the output includes Largest Contentful Paint (LCP) in milliseconds
AND the output includes First Input Delay (FID) or Total Blocking Time
AND the output includes Cumulative Layout Shift (CLS)
AND all metrics are captured from the dashboard page load
```

#### Scenario: Audit script detects accessibility violations
```
GIVEN the dashboard page is loaded in the browser
WHEN the script runs axe-core accessibility audit
THEN any WCAG violations are reported with:
  - Violation type (e.g., "color-contrast", "missing-alt-text")
  - Severity level (critical, serious, moderate, minor)
  - Affected element selectors
  - Suggested remediation
```

### Requirement: Network Request Monitoring
The audit MUST capture and report network activity during the user flow, including API calls, timing, and errors.

#### Scenario: Audit reports successful API calls
```
GIVEN the user flow triggers API requests to /api/dashboard
WHEN the audit script monitors network activity
THEN the report includes:
  - Request URL: http://localhost:8000/api/dashboard
  - HTTP method: GET
  - Status code: 200
  - Response time in milliseconds
  - Response size in bytes
```

#### Scenario: Audit detects failed API requests
```
GIVEN a user flow triggers a request to a failing endpoint
WHEN the audit script monitors network activity
THEN the report flags the failed request with:
  - Request URL
  - HTTP status code (e.g., 500, 404)
  - Error message from response body
  - Timestamp of failure
```

#### Scenario: Audit identifies slow requests
```
GIVEN the user flow includes multiple API calls
WHEN the audit script analyzes network timing
THEN the report highlights requests exceeding 500ms
AND lists them by response time in descending order
AND includes timing breakdown (DNS, TCP, TLS, request, response)
```

### Requirement: Console Error Detection
The audit MUST capture and report JavaScript console errors and warnings during the user flow.

#### Scenario: Audit reports console errors
```
GIVEN the user flow triggers a JavaScript error
WHEN the audit script monitors console output
THEN the report includes:
  - Error message
  - Stack trace
  - Source file and line number
  - Timestamp relative to page load
```

#### Scenario: Audit reports console warnings
```
GIVEN the page logs deprecation warnings
WHEN the audit script monitors console output
THEN the report includes all warnings with:
  - Warning message
  - Source context
  - Count of occurrences
```

### Requirement: Report Generation in Multiple Formats
The audit script MUST generate reports in both JSON (machine-readable) and HTML (human-readable) formats.

#### Scenario: JSON report contains structured data
```
GIVEN the audit has completed
WHEN the script generates the JSON report
THEN the file is saved as `audit-results-<timestamp>.json`
AND the JSON includes top-level keys: "timestamp", "environment", "performance", "accessibility", "network", "console"
AND all metrics are valid JSON data types
AND the file is valid JSON parseable by standard tools
```

#### Scenario: HTML report is readable by humans
```
GIVEN the audit has completed
WHEN the script generates the HTML report
THEN the file is saved as `audit-report-<timestamp>.html`
AND the report displays:
  - Summary dashboard with pass/fail indicators
  - Performance metrics with visual gauges
  - Accessibility violations in expandable sections
  - Network waterfall or table
  - Console errors grouped by severity
AND the HTML is styled with CSS for readability
```

### Requirement: Configurable Audit Scenarios
The audit script MUST support configuration to run different user flow scenarios via config file or CLI arguments.

#### Scenario: Audit runs custom scenario from config
```
GIVEN a config file `audit-config.json` defines:
  {
    "scenarios": [
      {"name": "login", "steps": ["navigate /login", "fill credentials", "submit"]},
      {"name": "dashboard", "steps": ["navigate /dashboard", "click stats", "wait for charts"]}
    ]
  }
WHEN the developer runs `npm run audit -- --config audit-config.json`
THEN the script executes both scenarios sequentially
AND generates separate reports for each scenario
```

#### Scenario: Audit accepts CLI override for target URL
```
GIVEN the default frontend URL is http://localhost:3000
WHEN the developer runs `npm run audit -- --url http://staging.example.com`
THEN the audit script targets the specified URL instead
AND all navigation and API calls use the new base URL
```

### Requirement: Screenshot Capture on Failure
The audit MUST capture screenshots when errors occur or assertions fail during the user flow.

#### Scenario: Screenshot captured on login failure
```
GIVEN the login flow fails due to incorrect credentials
WHEN the audit script detects the error
THEN a screenshot is saved as `error-login-<timestamp>.png`
AND the screenshot shows the current page state
AND the screenshot path is included in the audit report
```

#### Scenario: Screenshot captured on accessibility violation
```
GIVEN the page has critical accessibility violations
WHEN the audit script detects them
THEN a screenshot is saved highlighting the affected elements
AND the screenshot is linked in the HTML report
```

### Requirement: Audit Execution Integration with Process Management
The audit script MUST integrate with process management to start services, wait for health, run audit, and cleanup.

#### Scenario: End-to-end audit with automated service management
```
GIVEN the developer runs `scripts/run-full-audit.sh`
THEN the script:
  1. Starts backend and frontend via Docker Compose detached
  2. Waits for health checks to pass (max 60s)
  3. Runs the Chrome DevTools audit script
  4. Generates JSON and HTML reports
  5. Stops all services
  6. Exits with code 0 if audit passes, code 1 if failures detected
```

#### Scenario: Audit skips service start if already running
```
GIVEN backend and frontend are already running
WHEN the developer runs `scripts/run-full-audit.sh --skip-start`
THEN the script skips service startup
AND proceeds directly to health check verification
AND runs the audit against existing services
```

### Requirement: Audit Performance Budgets
The audit MUST support defining performance budgets and fail if thresholds are exceeded.

#### Scenario: Audit fails when LCP exceeds budget
```
GIVEN the performance budget defines LCP < 2500ms
WHEN the audit measures LCP of 3200ms
THEN the audit report flags LCP as "FAILED"
AND the exit code is 1
AND the HTML report highlights the violation in red
```

#### Scenario: Audit passes when all metrics within budget
```
GIVEN performance budgets are:
  - LCP < 2500ms
  - FID < 100ms
  - CLS < 0.1
WHEN the audit measures:
  - LCP: 1800ms
  - FID: 45ms
  - CLS: 0.05
THEN the audit report shows all metrics as "PASSED"
AND the exit code is 0
```

### Requirement: Parallel Audit Execution
The audit script MUST support running multiple user flow scenarios in parallel to reduce total execution time.

#### Scenario: Multiple scenarios run concurrently
```
GIVEN the audit config defines 3 independent scenarios
WHEN the developer runs `npm run audit -- --parallel`
THEN the script launches 3 browser contexts simultaneously
AND each context executes its scenario independently
AND reports are merged into a single output
AND total execution time is less than sequential execution
```

### Requirement: Connection indicator logging hook
Whenever the UI connection indicator changes status (ONLINE/LIVE/STANDBY/OFFLINE), the frontend MUST emit a structured console log (and optional metrics hook) so experience reports and telemetry can trace outage frequency.

#### Scenario: Console log on offline transition
- **WHEN** the indicator switches to OFFLINE
- **THEN** the app logs `connection-indicator:offline` with timestamp and relevant context (e.g., pipeline status)
- **AND** when connectivity resumes, a matching `connection-indicator:online` log is emitted.

### Requirement: Telemetry dispatcher for connection indicator
The frontend MUST expose a `window.__novelEngineTelemetry` (or equivalent) emitter that receives connection-indicator events so observability pipelines can collect outage stats.

#### Scenario: Telemetry event emitted on status change
- **WHEN** the connection indicator transitions (e.g., ONLINE → OFFLINE)
- **THEN** an event `{ type: 'connection-indicator', status, previous, timestamp }` is emitted via the dispatcher in addition to console logs.

### Requirement: Automated MCP dashboard capture
The project MUST provide a documented CLI script that launches headless Chrome, drives the landing CTA, captures the dashboard screenshot, and emits metadata for evidence tracking.

#### Scenario: Snapshot command succeeds
- **WHEN** developers run `node scripts/mcp_chrome_runner.js --url http://127.0.0.1:3000/dashboard`
- **THEN** the script auto-clicks the `data-testid="cta-demo"` button if the landing page is visible, waits for `data-role="control-cluster"` to render, and saves both a PNG and JSON file under `docs/assets/dashboard/`.
- **AND** the JSON records at minimum `title`, `url`, `connectionStatus`, `pipelinePhase`, and `viewport` so README/docs can reference the live layout state.

