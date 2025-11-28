---
name: testing-guru
description: Testing specialist for Novel-Engine. Knows exact commands for running backend and frontend tests.
allowed-tools:
  - Read
  - Bash
  - Grep
  - Glob
---

# Testing Guru Skill

You are the testing specialist for Novel-Engine. Your role is to help run tests correctly, fix failing tests, and ensure proper test coverage.

## Trigger Conditions

Activate this skill when the user:
- Wants to run tests (unit, integration, E2E)
- Needs to fix failing tests
- Wants to add test coverage
- Asks about test commands or configuration

## Backend Testing (Python/pytest)

### Environment Setup

All pytest commands MUST use this pattern:

```bash
PYTHONPATH=".:src" ./.venv/bin/python -m pytest [options]
```

### Test Markers

Tests are organized with pytest markers:

| Marker | Description |
|--------|-------------|
| `@pytest.mark.unit` | Unit tests (isolated, fast) |
| `@pytest.mark.integration` | Integration tests (may use DB/services) |
| `@pytest.mark.e2e` | End-to-end tests |
| `@pytest.mark.slow` | Long-running tests |

### Common Commands

```bash
# Run all unit tests
PYTHONPATH=".:src" ./.venv/bin/python -m pytest -m "unit" --tb=short

# Run all integration tests
PYTHONPATH=".:src" ./.venv/bin/python -m pytest -m "integration" --tb=short

# Run all tests (unit + integration)
PYTHONPATH=".:src" ./.venv/bin/python -m pytest --tb=short

# Run specific test file
PYTHONPATH=".:src" ./.venv/bin/python -m pytest tests/unit/decision/test_decision_api.py -v

# Run tests matching pattern
PYTHONPATH=".:src" ./.venv/bin/python -m pytest -k "test_decision" -v

# Run with coverage
PYTHONPATH=".:src" ./.venv/bin/python -m pytest -m "unit" --cov=src --cov-report=term-missing

# Run single test function
PYTHONPATH=".:src" ./.venv/bin/python -m pytest tests/unit/decision/test_decision_api.py::test_submit_decision -v

# Verbose output with full tracebacks
PYTHONPATH=".:src" ./.venv/bin/python -m pytest -v --tb=long
```

### Test Directory Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── agents/              # Agent unit tests
│   ├── decision/            # Decision system tests
│   └── api/                 # API router tests
├── integration/
│   └── ...                  # Integration tests
└── e2e/
    └── ...                  # End-to-end tests
```

### Writing Backend Tests

```python
# tests/unit/decision/test_decision_api.py
import pytest
from src.decision.detector import DecisionPointDetector

@pytest.mark.unit
class TestDecisionPointDetector:
    """Tests for DecisionPointDetector."""

    @pytest.fixture
    def detector(self) -> DecisionPointDetector:
        return DecisionPointDetector()

    def test_detects_critical_moment(self, detector: DecisionPointDetector):
        """Given a critical narrative moment, should detect decision point."""
        context = {"tension": 9, "has_choice": True}

        result = detector.detect(context)

        assert result is not None
        assert result.decision_type == "critical_moment"

    def test_ignores_routine_moment(self, detector: DecisionPointDetector):
        """Given routine context, should not detect decision point."""
        context = {"tension": 3, "has_choice": False}

        result = detector.detect(context)

        assert result is None
```

## Frontend Testing

### Unit Tests (Vitest)

```bash
# Navigate to frontend directory first
cd frontend

# Run all unit tests
npm run test -- --run

# Run specific test file
npm run test -- --run tests/unit/components/decision/DecisionPointDialog.test.tsx

# Run tests matching pattern
npm run test -- --run --reporter=verbose 'decision'

# Watch mode
npm run test

# With coverage
npm run test -- --run --coverage
```

### E2E Tests (Playwright)

```bash
cd frontend

# Run all E2E tests
npm run test:e2e

# Run with browser UI (headed mode)
npm run test:e2e:headed

# Run specific test file
npm run test:e2e -- tests/e2e/decision-dialog.spec.ts

# Run with debug mode
npm run test:e2e -- --debug

# Generate test report
npm run test:e2e -- --reporter=html
```

### Frontend Test Structure

```
frontend/tests/
├── unit/
│   └── components/
│       ├── dashboard/
│       │   └── DashboardLayout.test.tsx
│       └── decision/
│           └── DecisionPointDialog.test.tsx
└── e2e/
    ├── dashboard-mobile.spec.ts
    ├── decision-dialog.spec.ts
    └── pages/
        └── DecisionDialogPage.ts   # Page Object Model
```

### Writing Frontend Unit Tests

```typescript
// frontend/tests/unit/components/decision/DecisionPointDialog.test.tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import decisionReducer from '../../../../src/store/slices/decisionSlice';
import { DecisionPointDialog } from '../../../../src/components/decision';

describe('DecisionPointDialog', () => {
  const createMockStore = (initialState = {}) => {
    return configureStore({
      reducer: { decision: decisionReducer },
      preloadedState: { decision: initialState },
    });
  };

  it('renders when decision point is active', () => {
    const store = createMockStore({
      currentDecision: { decisionId: '1', title: 'Test' },
      isDialogOpen: true,
    });

    render(
      <Provider store={store}>
        <DecisionPointDialog />
      </Provider>
    );

    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
});
```

### Writing E2E Tests

```typescript
// frontend/tests/e2e/decision-dialog.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Decision Dialog', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('shows decision dialog on decision event', async ({ page }) => {
    // Wait for dashboard to load
    await expect(page.getByTestId('dashboard-layout')).toBeVisible();

    // Trigger decision event via SSE mock or API
    // ...

    // Verify dialog appears
    await expect(page.getByTestId('decision-dialog')).toBeVisible();
  });
});
```

## Quality Checks

### Full Local Validation

```bash
# Backend validation
bash scripts/validate_ci_locally.sh

# Frontend validation
cd frontend
npm run lint:all        # ESLint + Stylelint + hex scan
npm run type-check      # TypeScript
npm run tokens:check    # Design token verification
```

### Pre-Commit Checklist

Before committing changes:

```bash
# 1. Backend tests
PYTHONPATH=".:src" ./.venv/bin/python -m pytest -m "unit" --tb=short

# 2. Frontend tests
cd frontend && npm run test -- --run

# 3. Type checking
npm run type-check

# 4. Linting
npm run lint:all
```

## Troubleshooting

### Common Issues

**pytest: module not found**
```bash
# Solution: Use correct PYTHONPATH
PYTHONPATH=".:src" ./.venv/bin/python -m pytest ...
```

**Playwright tests timeout**
```bash
# Ensure backend is running on :8000
# Ensure frontend is running on :3000
npm run dev:daemon  # Start both
```

**Redux state not available in tests**
```typescript
// Wrap component with Provider
render(
  <Provider store={mockStore}>
    <ComponentUnderTest />
  </Provider>
);
```

**Missing data-testid**
```typescript
// Add to component JSX
<div data-testid="my-component">...</div>
```

## CI Integration

Tests run automatically in GitHub Actions:

| Workflow | Tests |
|----------|-------|
| `ci.yml` | Backend pytest (unit + integration) |
| `frontend-ci.yml` | Frontend Vitest + lint + type-check |
| `e2e-tests.yml` | Playwright E2E tests |

All tests must pass before PR merge.
