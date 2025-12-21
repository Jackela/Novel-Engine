# Proposal: Fix E2E Test CI Health Check Failures

## Why

E2E tests fail in CI with 503 Service Unavailable errors because:

1. **Masked failures**: `conftest.py` accepts 503 status code as valid during health checks, masking API startup failures
2. **Missing dependencies**: `e2e-tests.yml` workflow lacks PYTHONPATH configuration and test requirements installation
3. **No readiness verification**: Health check doesn't verify the API is actually functional before running tests

This causes E2E tests to pass locally but fail in CI, blocking merges.

## What Changes

### 1. Fix Health Check Logic (`tests/e2e/conftest.py`)
- Only accept HTTP 200 as successful health check
- Verify `service_status == "healthy"` in response body
- Add clear error messages when API fails to start
- Implement proper retry with exponential backoff

### 2. Update E2E Workflow (`.github/workflows/e2e-tests.yml`)
- Add `pip install -e .` for editable package installation
- Add `requirements/requirements-test.txt` to dependencies
- Set PYTHONPATH to include `src/` directory
- Add debug output for troubleshooting

### 3. Add API Readiness Assertion
- Fail fast if API doesn't become healthy within timeout
- Provide clear error message showing actual status vs expected

## Impact

- **Capability**: Updates `ci-parity` (ensures local and CI E2E tests behave identically)
- **Risk**: Low - only affects test infrastructure, not production code
- **Rollback**: Simple - revert the two file changes

## Success Criteria

1. E2E tests in CI either pass or fail with clear, actionable error messages
2. No more false-positive health checks (503 accepted as valid)
3. PYTHONPATH properly configured in CI environment
