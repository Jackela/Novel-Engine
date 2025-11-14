## ADDED Requirements

### Requirement: Dual-format Experience Reports
Playwright runs MUST generate both Markdown and HTML Experience Reports summarizing CTA/offline outcomes, screenshots, and status badges so stakeholders can review the run without extra tooling.

#### Scenario: HTML report attached to CI artifacts
- **WHEN** `npm run test:e2e` finishes
- **THEN** it produces `reports/experience-report-<timestamp>.md` and `.html`
- **AND** the HTML report includes pass/fail badges for CTA/offline tests, screenshot links, and timestamps.
