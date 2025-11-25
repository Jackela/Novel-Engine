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

- [ ] **Validation**
  - [ ] Push to PR and verify CI passes
  - [ ] Confirm error messages are clear when API fails

## Files Modified

| File | Change |
|------|--------|
| `tests/e2e/conftest.py` | Fixed health check to only accept 200 + healthy status |
| `.github/workflows/e2e-tests.yml` | Added PYTHONPATH, editable install, test requirements |

## Dependencies

- Depends on: `src/security/security_headers.py` being tracked (already fixed)
- Blocks: PR #18 merge
