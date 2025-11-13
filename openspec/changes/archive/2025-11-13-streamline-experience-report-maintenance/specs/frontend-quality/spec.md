## ADDED Requirements

### Requirement: Experience report retention and tagging
Experience report generation MUST retain only the latest N files and rely on explicit Playwright tags (e.g., `@experience-cta`, `@experience-offline`) when aggregating results.

#### Scenario: Reporter keeps latest files and finds tagged tests
- **GIVEN** multiple report files exist
- **WHEN** a new report is generated
- **THEN** only the most recent N files remain in `frontend/reports/`
- **AND** the reporter selects test results via tags, so renaming titles does not break the summary.
