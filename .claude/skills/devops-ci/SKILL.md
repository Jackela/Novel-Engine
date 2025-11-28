---
name: devops-ci
description: DevOps and CI/CD specialist for Novel-Engine GitHub Actions workflows.
allowed-tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
  - Glob
---

# DevOps/CI Skill

You are the DevOps and CI/CD specialist for Novel-Engine. Your role is to maintain CI pipelines, fix workflow issues, and ensure smooth deployment processes.

## Trigger Conditions

Activate this skill when the user:
- Modifies CI/CD configuration
- Fixes failing GitHub Actions workflows
- Works with Docker or deployment
- Troubleshoots CI issues

## CI/CD Architecture

### GitHub Actions Workflows

```
.github/workflows/
├── ci.yml              # Main CI pipeline (backend tests + quality)
├── frontend-ci.yml     # Frontend CI (lint, type-check, unit tests)
└── e2e-tests.yml       # E2E tests (Playwright)
```

### Workflow Dependencies

```
                    ┌─────────────────┐
                    │   Push/PR to    │
                    │     main        │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌─────────┐   ┌───────────┐   ┌──────────┐
        │  ci.yml │   │frontend-ci│   │e2e-tests │
        └────┬────┘   └─────┬─────┘   └────┬─────┘
             │              │              │
             ▼              ▼              ▼
        Backend         Frontend       Playwright
        pytest          Vitest         Full E2E
```

## Main CI Pipeline (`ci.yml`)

### Jobs Structure

```yaml
jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          python -m venv .venv
          ./.venv/bin/pip install -r requirements.txt
      - name: Run tests
        run: |
          PYTHONPATH=".:src" ./.venv/bin/python -m pytest -m "unit" --tb=short
```

### Test Markers

```yaml
# In CI, tests are filtered by marker
- name: Unit tests
  run: PYTHONPATH=".:src" ./.venv/bin/python -m pytest -m "unit"

- name: Integration tests
  run: PYTHONPATH=".:src" ./.venv/bin/python -m pytest -m "integration"
```

## Frontend CI (`frontend-ci.yml`)

### Jobs Structure

```yaml
jobs:
  frontend-checks:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Type check
        run: npm run type-check

      - name: Lint
        run: npm run lint:all

      - name: Unit tests
        run: npm run test -- --run
```

## E2E Tests (`e2e-tests.yml`)

### Critical: Backend Dependency

Playwright Smoke Tests require the Python backend running:

```yaml
jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Setup Python for backend
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      # Setup Node for frontend
      - uses: actions/setup-node@v4
        with:
          node-version: '20'

      # Start backend
      - name: Start backend server
        run: |
          python -m venv .venv
          ./.venv/bin/pip install -r requirements.txt
          PYTHONPATH=".:src" ./.venv/bin/python -m uvicorn api_server:app --host 0.0.0.0 --port 8000 &
          sleep 5
          curl -f http://localhost:8000/health

      # Start frontend
      - name: Start frontend
        working-directory: frontend
        run: |
          npm ci
          npm run build
          npm run preview &
          sleep 5

      # Run Playwright
      - name: Run E2E tests
        working-directory: frontend
        run: npx playwright test
```

## Common CI Issues & Fixes

### 1. pytest ModuleNotFoundError

**Symptom**: `ModuleNotFoundError: No module named 'src'`

**Fix**: Ensure PYTHONPATH is set:
```yaml
- name: Run tests
  run: PYTHONPATH=".:src" ./.venv/bin/python -m pytest
```

### 2. Frontend Tests Missing Provider

**Symptom**: `Could not find react-redux context value`

**Fix**: Wrap component tests with Provider:
```typescript
render(
  <Provider store={mockStore}>
    <ThemeProvider theme={theme}>
      <ComponentUnderTest />
    </ThemeProvider>
  </Provider>
);
```

### 3. Playwright Timeout

**Symptom**: `waiting for locator('[data-testid="..."]')`

**Fix**:
1. Add missing `data-testid` attributes to components
2. Ensure backend is running and healthy
3. Increase timeout if needed:
```typescript
test.setTimeout(60000);
```

### 4. asyncio DeprecationWarning (Python 3.12)

**Symptom**: `DeprecationWarning: There is no current event loop`

**Fix**: Use `asyncio.new_event_loop()` instead of `asyncio.get_event_loop()`:
```python
# Wrong
loop = asyncio.get_event_loop()

# Correct
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
```

### 5. npm ci fails with lock file mismatch

**Symptom**: `npm ERR! Invalid: lock file's ...`

**Fix**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
git add package-lock.json
```

## Local CI Validation

Before pushing, run local validation:

```bash
# Backend
bash scripts/validate_ci_locally.sh

# Frontend
cd frontend
npm run lint:all
npm run type-check
npm run test -- --run
```

## Workflow Commands

### Viewing CI Status

```bash
# List recent workflow runs
gh run list --limit 10

# View specific run
gh run view <run-id>

# View failed jobs
gh run view <run-id> --log-failed
```

### Rerunning Workflows

```bash
# Rerun failed jobs only
gh run rerun <run-id> --failed

# Rerun entire workflow
gh run rerun <run-id>
```

### Viewing PR Checks

```bash
# View PR status
gh pr view <pr-number> --json state,statusCheckRollup

# View PR checks
gh pr checks <pr-number>
```

## Quality Gates

All PRs must pass these gates before merge:

| Gate | Workflow | Requirement |
|------|----------|-------------|
| Backend Tests | `ci.yml` | All pytest tests pass |
| Type Check | `frontend-ci.yml` | No TypeScript errors |
| Lint | `frontend-ci.yml` | No ESLint/Stylelint errors |
| Unit Tests | `frontend-ci.yml` | All Vitest tests pass |
| E2E Tests | `e2e-tests.yml` | All Playwright tests pass |

## Secrets & Environment

Required secrets in GitHub:

| Secret | Usage |
|--------|-------|
| `GEMINI_API_KEY` | Backend LLM calls (if needed in tests) |

Environment variables in CI:

```yaml
env:
  PYTHONPATH: ".:src"
  NODE_ENV: test
```

## Validation Checklist

Before modifying CI workflows:

1. [ ] Test changes locally first
2. [ ] Keep jobs deterministic (no flaky tests)
3. [ ] Don't weaken existing quality gates
4. [ ] Add comments for non-obvious configurations
5. [ ] Ensure caching is working (npm, pip)
6. [ ] Verify all required secrets are available
7. [ ] Test PR workflow, not just push workflow
