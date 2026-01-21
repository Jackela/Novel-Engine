# docs-alignment Specification

## Purpose
Keep project-facing documentation (README + docs hub) aligned with the currently validated development workflow, without committing transient report artifacts.
## Requirements
### Requirement: README and Process Docs Reflect Validated Workflow
Project-facing documentation (README, README.en, `docs/index.md`, primary runbooks) MUST match the currently validated startup + regression workflow.

#### Scenario: Quick start references current commands
- **GIVEN** backend/frontend bootstrap commands or validation scripts change
- **WHEN** a contributor reads the README quick-start section
- **THEN** it lists the exact shell commands (including the new non-blocking script, cleanup helper, lint/type-check/test suite, Playwright smoke, and act invocations) that were last executed successfully, with timestamps where applicable.

#### Scenario: Regression suite listed alongside verification evidence
- **GIVEN** we rely on README/docs to communicate trustworthy quality signals
- **WHEN** someone inspects `docs/index.md` or related runbooks
- **THEN** they find the current regression checklist (lint/type-check/vitest/playwright/act) and pointers to CI artifacts so they can reproduce or audit without searching the repo manually.

### Requirement: Dashboard Evidence Assets Stay Fresh
The repo MUST maintain up-to-date UI evidence (screenshots) captured from the running application and referenced in documentation.

#### Scenario: README embeds latest dashboard screenshot
- **GIVEN** the dashboard layout changes (flow layout, quick actions tile, etc.)
- **WHEN** we land the update, we must capture new Chrome DevTools screenshots via MCP, store them under `docs/assets/` with metadata (capture date + commit), and update README/UX docs to reference the new files.
- **AND** documentation explains how to rerun the capture (commands + Chrome DevTools steps) so the evidence can be refreshed after future visual changes.

### Requirement: Onboarding docs cover demo CTA + offline simulation
The README/onboarding documentation MUST include instructions for:
- Running the demo CTA flow locally (including any env vars)
- Simulating offline mode and interpreting the connection indicator
- Understanding `PLAYWRIGHT_VERIFY_ATTEMPTS` and `PLAYWRIGHT_VERIFY_RETRY_DELAY`
- Locating the Experience Report artifacts.

#### Scenario: README guidance present
- **WHEN** a new contributor reads the README/onboarding doc
- **THEN** they find sections that describe how to run the landing CTA, trigger offline simulation, configure the verify env vars, and download the report from CI artifacts.

### Requirement: Document report artifacts and telemetry API
README/onboarding docs MUST explain how to download the HTML/Markdown reports from CI, interpret summary badges, and subscribe to the telemetry dispatcher for connection events.

#### Scenario: Contributor can follow docs
- **WHEN** a new contributor reads the docs
- **THEN** they find steps for locating the Experience Report artifacts, screenshots of the HTML summary, and sample code for listening to `window.__novelEngineTelemetry` events.

### Requirement: Document CI job summary location
Documentation MUST state that the Experience Report summary is available in the GitHub job summary (alongside download instructions for full artifacts).

#### Scenario: README/onboarding describes job summary
- **WHEN** a contributor reads the docs
- **THEN** they learn that the Playwright workflow posts a CTA/offline table to the job summary and where to find the full report links.
