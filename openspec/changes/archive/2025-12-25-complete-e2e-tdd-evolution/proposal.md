# Proposal: Complete E2E Test Suite & TDD Evolution

## Summary

Complete the E2E test suite to achieve full coverage of all application routes and user flows, fix any discovered issues through TDD-driven development, and establish continuous project evolution practices following SOLID and SSOT principles.

## Motivation

### Current State

The Novel-Engine frontend has partial E2E test coverage:

**Existing E2E Tests:**
- Dashboard core/extended UAT tests
- Dashboard interactions and mobile tests
- Login flow tests
- Accessibility tests
- Decision dialog tests

**Coverage Gaps:**
1. **Landing Page** - No dedicated E2E test for `/` route
2. **Navigation Flows** - Landing → Dashboard transition not tested
3. **Error Boundaries** - Error state handling not covered
4. **Mobile Responsive** - Landing page mobile tests deferred
5. **Auth Edge Cases** - Protected route redirect scenarios

### Recent Audit Findings (2025-11-29)

The UI audit identified:
- All critical issues have been RESOLVED
- Remaining P3: Landing page initial render performance
- Remaining P3: Complete mobile responsive testing

### Why Now

1. **Stability achieved** - Core functionality is working; time to lock in behavior with tests
2. **TDD foundation** - Establishing test-first workflow prevents future regressions
3. **SOLID/SSOT compliance** - Tests enforce architectural boundaries and single sources of truth

## Scope

### In Scope

1. **E2E Route Coverage**
   - Landing page E2E tests (`/`)
   - Protected route redirect tests (`/dashboard` unauthenticated)
   - Login page tests (`/login`)
   - 404/wildcard redirect tests (`/*`)

2. **E2E User Flows**
   - Complete user journey: Landing → Auth → Dashboard
   - Navigation between all routes
   - Error boundary triggering and recovery

3. **TDD Workflow**
   - Test-first development process documentation
   - Pre-commit hooks for test execution
   - Coverage thresholds enforcement

### Out of Scope

- Backend API tests (covered separately)
- Visual regression tests (future enhancement)
- Performance benchmarking (separate initiative)

## Impact

### Capabilities Affected

| Capability | Change Type | Description |
|------------|-------------|-------------|
| e2e-route-coverage | ADDED | Full route E2E test coverage |
| e2e-user-flows | ADDED | Complete user journey tests |
| tdd-workflow | ADDED | TDD process and enforcement |

### Dependencies

- Existing `test-pyramid-compliance` spec
- Existing `frontend-quality` spec
- Playwright test infrastructure

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Test flakiness | Medium | High | Use stable selectors, proper waits |
| CI slowdown | Low | Medium | Parallel test execution |
| Maintenance burden | Low | Medium | Clear test organization |

## Success Criteria

1. All routes have E2E test coverage
2. Complete user journey tests pass
3. TDD workflow documented and enforced
4. Coverage threshold >= 80% for E2E-covered components
5. No test flakiness in CI (3 consecutive green runs)
