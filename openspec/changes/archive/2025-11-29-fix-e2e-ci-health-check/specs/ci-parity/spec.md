# ci-parity Specification Delta

## ADDED Requirements

### Requirement: E2E Test API Health Verification
E2E tests MUST verify that the API server is fully healthy before executing tests, with clear failure messages when the server fails to start.

#### Scenario: API health check rejects partial startup
- **GIVEN** the E2E test suite starts and attempts to verify API readiness
- **WHEN** the API returns HTTP 503 (Service Unavailable) or any non-200 status
- **THEN** the health check MUST NOT consider this successful, MUST continue retrying until timeout, and MUST fail with a clear error message indicating the actual status code received

#### Scenario: API health check validates response body
- **GIVEN** the E2E test suite receives HTTP 200 from the health endpoint
- **WHEN** the response body does not contain `"service_status": "healthy"`
- **THEN** the health check MUST fail with an error message showing the actual service status

#### Scenario: CI workflow has complete Python environment
- **GIVEN** the E2E test workflow runs in GitHub Actions
- **WHEN** the workflow installs dependencies
- **THEN** it MUST set PYTHONPATH to include both project root and src/, install the project in editable mode (`pip install -e .`), and install test requirements from `requirements/requirements-test.txt`
