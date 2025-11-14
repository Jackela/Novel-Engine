## ADDED Requirements

### Requirement: Report cleanup in workflows
CI and local workflows that generate experience reports MUST enforce the retention rule (clean up older files) to keep working directories tidy.

#### Scenario: CI run prunes old reports
- **WHEN** the GitHub workflow runs Playwright + report generation
- **THEN** it automatically prunes reports beyond the retention limit before uploading artifacts.
