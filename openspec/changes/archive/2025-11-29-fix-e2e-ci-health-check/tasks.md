# Tasks: Fix E2E Test CI Health Check Failures

## Implementation Checklist

- [x] **Fix conftest.py health check**
  - [x] Remove 503 from accepted status codes
  - [x] Add response body validation (`service_status == "healthy"`)
  - [x] Improve error messages for startup failures

- [x] **Update e2e-tests.yml workflow**
  - [x] Add `pip install -e .` step
  - [x] Add `requirements/requirements-test.txt` installation
  - [x] Set PYTHONPATH environment variable
  - [x] Add debug step to verify Python environment

- [x] **Fix health endpoint returning 400 instead of 503**
  - [x] Return 503 directly when health_monitor not initialized (avoids global exception handler)
  - [x] Set service_status to "initializing" during startup phase

- [x] **Validation**
  - [x] Push to PR - changes deployed (commits 2a71a3c, 549ce72, 31c2718)
  - [x] Confirm error messages are clear - health endpoint now returns 503 with "initializing" status

## Outcome

**Achieved:**
- Health check no longer returns misleading 400 Bad Request
- Health endpoint returns proper 503 with `service_status: "initializing"` during startup
- E2E workflow has correct PYTHONPATH and dependencies
- conftest.py only accepts truly healthy status (200 + "healthy")

**Known Issue (out of scope):**
- E2E tests still fail because `SystemOrchestrator.startup()` hangs/fails in CI
- This is a separate issue requiring investigation into orchestrator CI compatibility
- The health check fix is working correctly - tests now fail with clear error vs. silent 400

## Files Modified

| File | Change |
|------|--------|
| `tests/e2e/conftest.py` | Fixed health check to only accept 200 + healthy status |
| `.github/workflows/e2e-tests.yml` | Added PYTHONPATH, editable install, test requirements |
| `src/api/main_api_server.py` | Fixed health endpoint to return 503 (not 400) when uninitialized |
