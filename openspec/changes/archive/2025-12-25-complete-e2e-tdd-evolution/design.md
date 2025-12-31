# Design: Complete E2E Test Suite & TDD Evolution

## Overview

This document describes the architectural decisions for completing the E2E test suite and establishing a TDD-driven development workflow.

## E2E Test Architecture

### Test Organization

```
frontend/tests/e2e/
├── landing-page.spec.ts      # Landing page tests (NEW)
├── protected-routes.spec.ts  # Auth/protected route tests (NEW)
├── navigation-flows.spec.ts  # Navigation and routing tests (NEW)
├── user-journey.spec.ts      # Complete user journey tests (NEW)
├── error-boundaries.spec.ts  # Error handling tests (NEW)
├── dashboard-core-uat.spec.ts        # (existing)
├── dashboard-extended-uat.spec.ts    # (existing)
├── dashboard-interactions.spec.ts    # (existing)
├── dashboard-mobile.spec.ts          # (existing)
├── dashboard-cross-browser-uat.spec.ts # (existing)
├── login-flow.spec.ts                # (existing - extend)
├── accessibility.spec.ts             # (existing)
└── decision-dialog.spec.ts           # (existing)
```

### Test Naming Convention

- `<feature>.spec.ts` - Feature-specific tests
- `<feature>-uat.spec.ts` - User acceptance tests
- `<feature>-mobile.spec.ts` - Mobile-specific tests

### Route Coverage Matrix

| Route | Test File | Coverage |
|-------|-----------|----------|
| `/` | `landing-page.spec.ts` | Full |
| `/dashboard` | `dashboard-*.spec.ts` | Full |
| `/login` | `login-flow.spec.ts` | Extended |
| `/*` (wildcard) | `navigation-flows.spec.ts` | Full |

## TDD Workflow Design

### Development Cycle

```
┌─────────────────────────────────────────────────┐
│                  TDD Cycle                       │
│                                                  │
│   ┌───────┐    ┌───────┐    ┌──────────┐       │
│   │  RED  │───▶│ GREEN │───▶│ REFACTOR │       │
│   └───────┘    └───────┘    └──────────┘       │
│       │                           │             │
│       │      Write failing        │             │
│       │      test first           │             │
│       │                           │             │
│       └───────────────────────────┘             │
│                                                  │
└─────────────────────────────────────────────────┘
```

### Test Layers (Test Pyramid)

```
        ╱╲
       ╱  ╲     E2E Tests (Playwright)
      ╱────╲    - User journeys
     ╱      ╲   - Critical paths
    ╱────────╲
   ╱          ╲  Integration Tests (Vitest)
  ╱────────────╲ - Component interactions
 ╱              ╲- API mocking
╱────────────────╲
                  Unit Tests (Vitest)
                  - Pure functions
                  - Isolated components
```

### Pre-commit Workflow

```bash
# .husky/pre-commit (proposed)
#!/bin/sh
npm run type-check
npm run lint
npm run test -- --run --changed
```

## SOLID Principles Application

### Single Responsibility (SRP)
- Each test file covers one feature/route
- Test helpers separated from test logic
- Page objects encapsulate page interactions

### Open/Closed (OCP)
- Test fixtures extensible without modification
- Base test setup reusable across test files

### Liskov Substitution (LSP)
- Page objects interchangeable for similar pages
- Test utilities work with any Playwright page

### Interface Segregation (ISP)
- Small, focused test helper functions
- Separate selectors from test logic

### Dependency Inversion (DIP)
- Tests depend on abstractions (page objects)
- Not on concrete implementations

## SSOT (Single Source of Truth)

### Canonical Sources

| Concern | Source Location |
|---------|-----------------|
| Selectors | `frontend/tests/e2e/selectors.ts` |
| Test fixtures | `frontend/tests/e2e/fixtures/` |
| Auth helpers | `frontend/tests/e2e/helpers/auth.ts` |
| Route constants | `frontend/src/routes.ts` |

### Avoiding Duplication

- Selectors defined once, used everywhere
- Auth flow abstracted to helper
- Route paths imported from source

## Test Data Strategy

### Mock Data
- Use factories for test data generation
- Consistent seed for deterministic tests

### API Mocking
- Playwright route handlers for API mocking
- Fallback to real API for smoke tests

## CI Integration

### Parallel Execution
```yaml
# playwright.config.ts
{
  workers: process.env.CI ? 4 : undefined,
  retries: process.env.CI ? 2 : 0,
}
```

### Artifact Collection
- Screenshots on failure
- Video recording for failed tests
- Trace files for debugging

## Migration Path

1. **Phase 1**: Add new E2E tests (no breaking changes)
2. **Phase 2**: Introduce TDD workflow documentation
3. **Phase 3**: Add pre-commit hooks (opt-in initially)
4. **Phase 4**: Enforce coverage thresholds
