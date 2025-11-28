# CI Runner Skill

Run CI checks locally to match GitHub Actions workflows before pushing code.

## Quick Check (Fast, ~2-3 minutes)

Run these first to catch obvious issues:

```bash
# Python syntax check
find . -name "*.py" -path "*/src/*" | xargs python3 -m py_compile

# Frontend type-check
cd frontend && npm run type-check

# Frontend lint
cd frontend && npm run lint
```

## Full CI Check

### Backend Tests

| GitHub Actions Job | Local Command |
|-------------------|---------------|
| `test-pyramid-check` | `python scripts/testing/test-pyramid-monitor-fast.py` |
| `validate-markers` | `python scripts/testing/validate-test-markers.py --all --verbose` |
| `unit-tests` | `PYTHONPATH=".:src" ./.venv/bin/python -m pytest -m "unit" --tb=short` |
| `integration-tests` | `PYTHONPATH=".:src" ./.venv/bin/python -m pytest -m "integration" --tb=short` |
| `e2e-tests` | `PYTHONPATH=".:src" ./.venv/bin/python -m pytest -m "e2e" --tb=short` |
| `smoke-tests` | `PYTHONPATH=".:src" ./.venv/bin/python -m pytest -m "smoke" --tb=short` |

### Frontend Tests

| GitHub Actions Job | Local Command |
|-------------------|---------------|
| `type-check` | `cd frontend && npm run type-check` |
| `lint` | `cd frontend && npm run lint` |
| `unit-tests` | `cd frontend && npm run test -- --run` |
| `build` | `cd frontend && npm run build` |

## Execution Order

### Phase 1: Quick Validation (~1-2 min)
```bash
# Run in parallel
python scripts/testing/validate-test-markers.py --all
cd frontend && npm run type-check
cd frontend && npm run lint
```

### Phase 2: Unit Tests (~5-10 min)
```bash
# Backend unit tests
PYTHONPATH=".:src" ./.venv/bin/python -m pytest -m "unit" --tb=short

# Frontend unit tests
cd frontend && npm run test -- --run
```

### Phase 3: Integration & Build (~5-10 min)
```bash
# Backend integration tests
PYTHONPATH=".:src" ./.venv/bin/python -m pytest -m "integration" --tb=short

# Frontend build
cd frontend && npm run build
```

### Phase 4: E2E & Smoke (Optional, ~10+ min)
```bash
# Backend E2E tests
PYTHONPATH=".:src" ./.venv/bin/python -m pytest -m "e2e" --tb=short

# Backend smoke tests
PYTHONPATH=".:src" ./.venv/bin/python -m pytest -m "smoke" --tb=short
```

## Common Issues & Fixes

### Lint Errors

**Pre-existing lint errors** (not from your changes):
- `DashboardLayout.tsx`: unused `theme` variable
- `MfdModeSelector.tsx`: react-refresh warning
- `DecisionPointDialog.tsx`: unused import
- `useRealtimeEvents.ts`: missing dependency warning
- `decisionAPI.ts`: unused import
- `decisionSlice.test.ts`: unused imports

These are tracked issues and do not block CI. Check if errors are from your changes before investigating.

### Test Markers

All tests must have a pyramid marker (`@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`, or `@pytest.mark.smoke`).

To validate:
```bash
python scripts/testing/validate-test-markers.py --all --verbose
```

### Python Import Errors

Ensure `PYTHONPATH` includes both `.` and `src`:
```bash
PYTHONPATH=".:src" ./.venv/bin/python -m pytest ...
```

### Frontend Build Failures

1. Clear Vite cache: `rm -rf frontend/node_modules/.vite`
2. Reinstall deps: `cd frontend && npm ci`
3. Check for TypeScript errors first: `npm run type-check`

## CI Workflow Files

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | Backend CI (pytest, markers) |
| `.github/workflows/frontend-ci.yml` | Frontend CI (lint, test, build) |

## Related Skills

- `testing-guru` - Detailed testing commands and patterns
- `devops-ci` - CI/CD pipeline configuration
