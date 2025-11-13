## ADDED Requirements

### Requirement: Publish experience summary to CI job output
Playwright jobs MUST append a condensed experience summary (CTA/offline statuses and links to full reports) to the CI job summary so reviewers can see results without downloading artifacts.

#### Scenario: GitHub job summary shows CTA/offline table
- **WHEN** the Playwright workflow completes in CI
- **THEN** `$GITHUB_STEP_SUMMARY` contains a Markdown table with Demo CTA + offline recovery statuses and a link to the HTML/Markdown report artifacts.
