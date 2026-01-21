# frontend-quality Specification

## Purpose
TBD - created by archiving change add-dashboard-e2e-coverage. Update Purpose after archive.
## Requirements
### Requirement: Login E2E Coverage
The Playwright suite MUST include a login spec that covers successful authentication, inline error handling, and skip-link focus behavior.

#### Scenario: Successful login
- **GIVEN** valid credentials (or demo mode)
- **WHEN** the E2E spec submits the form
- **THEN** it waits for dashboard navigation and asserts the skip link can move focus to `#main-content`.

#### Scenario: Inline errors
- **GIVEN** invalid credentials
- **WHEN** the spec submits the form
- **THEN** the inline error message appears and the submit button returns to idle state within 5s.

### Requirement: Dashboard Interaction E2E Coverage
The suite MUST exercise major dashboard interactions (map selection, quick actions, pipeline states) on both desktop and tablet viewports.

#### Scenario: Map entity selection
- **WHEN** the spec clicks/activates each map entity
- **THEN** the selected state toggles and the tile status text updates without JS errors.

#### Scenario: Quick action toggles
- **WHEN** the spec triggers Start/Pause/Stop actions
- **THEN** the pipeline tile reflects the state in under 5s and the quick action buttons disable/enable accordingly.

### Requirement: Accessible Form Labels
Every visible form label in the frontend MUST either wrap its control or reference it via `htmlFor/id` so assistive tech can announce the association and eslint’s `label-has-associated-control` rule stays green.

#### Scenario: Labeled text inputs
- **GIVEN** a form control such as the API key input in `AgentInterface`
- **WHEN** the control renders
- **THEN** the markup includes either `<label><input .../></label>` or matching `id/htmlFor`
- **AND** `npm run lint` reports zero `label-has-associated-control` violations.

### Requirement: Keyboard-Accessible Interactive Elements
Any UI element that handles pointer clicks MUST either be a semantic button/link or expose the correct role, `tabIndex`, and `Enter/Space` key handlers so keyboard and assistive users can trigger it. Non-semantic containers without those affordances are not allowed.

#### Scenario: Clickable dashboard cards
- **GIVEN** a tile (e.g., status rows in `NarrativeDisplay.tsx`) that uses `onClick`
- **WHEN** a keyboard user tabs to it
- **THEN** the element is focusable, announces an appropriate role, and responds to `Enter`/`Space`
- **AND** `npm run lint` no longer reports `click-events-have-key-events` errors.

### Requirement: Quick E2E Smoke Coverage
The repo MUST include a lightweight Playwright spec that exercises a core dashboard happy path and is callable via `npm run test:e2e -- quick-e2e.spec.js`, ensuring CI has a fast smoke gate.

#### Scenario: Smoke command finds tests
- **WHEN** a developer runs `npm run test:e2e -- quick-e2e.spec.js`
- **THEN** Playwright discovers the referenced spec file, executes at least one test that reaches `/dashboard`, and exits 0 on pass (non-zero on failure)
- **AND** CI logs no “No tests found” errors for that command.

### Requirement: Demo CTA end-to-end coverage
The Playwright suite MUST include a test that begins at the landing route (`/`), triggers the "View Demo" CTA, observes the guest banner, and verifies the dashboard renders without bypass flags so regressions in the entry experience are caught automatically.

#### Scenario: Landing CTA opens guest dashboard
- **GIVEN** the Playwright spec starts without a session at `/`
- **WHEN** it activates the `data-testid="cta-demo"` button
- **THEN** it waits for navigation to `/dashboard`, asserts the guest banner (`data-testid="guest-mode-banner"`) is visible, and confirms the Summary Strip reports demo state
- **AND** the spec runs under the default CI command (no `SKIP_DASHBOARD_VERIFY`), ensuring the real user journey is exercised.

### Requirement: Experience Report for demo CTA flow
Playwright runs MUST produce a Markdown or HTML "Experience Report" summarizing the landing CTA journey, guest banner state, summary strip demo status, and offline indicator behaviour so stakeholders can review each run without digging into raw logs.

#### Scenario: Report emitted after Playwright run
- **WHEN** `npm run test:e2e` completes
- **THEN** a file `reports/experience-report.<md|html>` is generated containing:
  - CTA activation outcome
  - Guest banner visibility status
  - Summary strip mode (LIVE/ONLINE/OFFLINE)
  - Offline simulation results (if executed)
  - Links/paths to relevant screenshots
- **AND** CI stores the report as an artifact for download.

### Requirement: Dual-format Experience Reports
Playwright runs MUST generate both Markdown and HTML Experience Reports summarizing CTA/offline outcomes, screenshots, and status badges so stakeholders can review the run without extra tooling.

#### Scenario: HTML report attached to CI artifacts
- **WHEN** `npm run test:e2e` finishes
- **THEN** it produces `reports/experience-report-<timestamp>.md` and `.html`
- **AND** the HTML report includes pass/fail badges for CTA/offline tests, screenshot links, and timestamps.

### Requirement: Experience report retention and tagging
Experience report generation MUST retain only the latest N files and rely on explicit Playwright tags (e.g., `@experience-cta`, `@experience-offline`) when aggregating results.

#### Scenario: Reporter keeps latest files and finds tagged tests
- **GIVEN** multiple report files exist
- **WHEN** a new report is generated
- **THEN** only the most recent N files remain in `frontend/reports/`
- **AND** the reporter selects test results via tags, so renaming titles does not break the summary.

