## ADDED Requirements

### Requirement: Demo CTA end-to-end coverage
The Playwright suite MUST include a test that begins at the landing route (`/`), triggers the "View Demo" CTA, observes the guest banner, and verifies the dashboard renders without bypass flags so regressions in the entry experience are caught automatically.

#### Scenario: Landing CTA opens guest dashboard
- **GIVEN** the Playwright spec starts without a session at `/`
- **WHEN** it activates the `data-testid="cta-demo"` button
- **THEN** it waits for navigation to `/dashboard`, asserts the guest banner (`data-testid="guest-mode-banner"`) is visible, and confirms the Summary Strip reports demo state
- **AND** the spec runs under the default CI command (no `SKIP_DASHBOARD_VERIFY`), ensuring the real user journey is exercised.
