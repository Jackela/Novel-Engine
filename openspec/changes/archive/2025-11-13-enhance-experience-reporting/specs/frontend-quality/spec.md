## ADDED Requirements

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
