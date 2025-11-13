## ADDED Requirements

### Requirement: Onboarding docs cover demo CTA + offline simulation
The README/onboarding documentation MUST include instructions for:
- Running the demo CTA flow locally (including any env vars)
- Simulating offline mode and interpreting the connection indicator
- Understanding `PLAYWRIGHT_VERIFY_ATTEMPTS` and `PLAYWRIGHT_VERIFY_RETRY_DELAY`
- Locating the Experience Report artifacts.

#### Scenario: README guidance present
- **WHEN** a new contributor reads the README/onboarding doc
- **THEN** they find sections that describe how to run the landing CTA, trigger offline simulation, configure the verify env vars, and download the report from CI artifacts.
