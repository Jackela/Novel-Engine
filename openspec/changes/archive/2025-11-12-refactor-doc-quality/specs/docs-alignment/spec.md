## ADDED Requirements
### Requirement: README and Process Docs Reflect Validated Workflow
Project-facing documentation (README, README.en, docs/INDEX, primary runbooks) MUST match the currently validated startup + regression workflow.

#### Scenario: Quick start references current commands
- **GIVEN** backend/frontend bootstrap commands or validation scripts change
- **WHEN** a contributor reads the README quick-start section
- **THEN** it lists the exact shell commands (including the new non-blocking script, cleanup helper, lint/type-check/test suite, Playwright smoke, and act invocations) that were last executed successfully, with timestamps where applicable.

#### Scenario: Regression suite listed alongside verification evidence
- **GIVEN** we rely on README/docs to communicate trustworthy quality signals
- **WHEN** someone inspects `docs/INDEX.md` or related runbooks
- **THEN** they find the current regression checklist (lint/type-check/vitest/playwright/act) and links to latest reports under `reports/` so they can reproduce or audit without searching the repo manually.

### Requirement: Dashboard Evidence Assets Stay Fresh
The repo MUST maintain up-to-date UI evidence (screenshots) captured from the running application and referenced in documentation.

#### Scenario: README embeds latest dashboard screenshot
- **GIVEN** the dashboard layout changes (flow layout, quick actions tile, etc.)
- **WHEN** we land the update, we must capture new Chrome DevTools screenshots via MCP, store them under `docs/assets/` with metadata (capture date + commit), and update README/UX docs to reference the new files.
- **AND** documentation explains how to rerun the capture (commands + Chrome DevTools steps) so the evidence can be refreshed after future visual changes.
