## ADDED Requirements

### Requirement: Playwright smoke vs full pipelines
The CI pipeline MUST provide two Playwright tracks: a <1 minute smoke run for PR validation and the existing full suite for nightly/merge events, ensuring faster feedback while preserving coverage.

#### Scenario: Smoke run for PRs
- **GIVEN** a PR workflow runs `npm run test:e2e:smoke`
- **THEN** it executes a curated subset (CTA + offline tests) and finishes in under 60 seconds.

#### Scenario: Full run for nightly/main
- **GIVEN** the nightly or main-branch workflow
- **WHEN** it runs `npm run test:e2e`
- **THEN** the existing full suite executes, generating the Experience Report and attaching artifacts.
