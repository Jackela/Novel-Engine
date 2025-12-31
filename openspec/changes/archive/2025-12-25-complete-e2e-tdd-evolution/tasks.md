# Tasks: Complete E2E Test Suite & TDD Evolution

## Phase 1: E2E Route Coverage (Priority: High) ✅

### 1.1 Landing Page E2E Tests ✅
- [x] Create `frontend/tests/e2e/landing-page.spec.ts`
- [x] Test: Page loads with correct title and content
- [x] Test: "Launch Engine" button navigates to dashboard
- [x] Test: Feature cards render correctly
- [x] Test: Responsive layout at different viewports
- [ ] Verify: All tests pass in CI

### 1.2 Protected Route Tests ✅
- [x] Create `frontend/tests/e2e/protected-routes.spec.ts`
- [x] Test: Unauthenticated user redirected from `/dashboard` to `/`
- [x] Test: Authenticated user can access `/dashboard`
- [x] Test: Auth state persists across page refresh
- [ ] Verify: All tests pass in CI

### 1.3 Login Page Tests ✅
- [x] Extend `frontend/tests/e2e/login-flow.spec.ts`
- [x] Test: Login placeholder renders correctly
- [x] Test: Navigation to login from protected route
- [ ] Verify: All tests pass in CI

### 1.4 Wildcard Route Tests ✅
- [x] Create `frontend/tests/e2e/navigation.spec.ts`
- [x] Test: Unknown routes redirect to `/`
- [x] Test: Deep unknown paths redirect to `/`
- [ ] Verify: All tests pass in CI

## Phase 2: E2E User Flows (Priority: High) ✅

### 2.1 Complete User Journey Test ✅
- [x] Create `frontend/tests/e2e/user-journey.spec.ts`
- [x] Test: Landing → Launch Engine → Dashboard flow
- [x] Test: Dashboard interactions → Activity Stream updates
- [x] Test: Returning user session persistence
- [ ] Verify: All tests pass in CI

### 2.2 Error Boundary Tests ✅
- [x] Create `frontend/tests/e2e/error-boundaries.spec.ts`
- [x] Test: Error boundary catches network errors gracefully
- [x] Test: Application remains usable after errors
- [x] Test: Error recovery via page refresh
- [ ] Verify: All tests pass in CI

### 2.3 Navigation Flow Tests ✅
- [x] Create `frontend/tests/e2e/navigation-flows.spec.ts`
- [x] Test: Back/forward browser navigation
- [x] Test: Direct URL navigation
- [x] Test: Hash and query parameter handling
- [ ] Verify: All tests pass in CI

## Phase 3: TDD Workflow (Priority: Medium) ✅

### 3.1 Documentation ✅
- [x] Update `frontend/CLAUDE.md` with TDD workflow section
- [x] Document test-first development process
- [x] Add examples of proper test structure (E2E and Unit templates)

### 3.2 Pre-commit Hooks ✅
- [x] Add pre-commit hook for type-check
- [x] Add pre-commit hook for lint
- [ ] Configure selective test running on changed files

### 3.3 Coverage Enforcement ✅
- [x] Configure Vitest coverage thresholds
- [ ] Configure Playwright coverage reporting
- [ ] Add CI check for coverage regression

## Phase 4: Code Quality Gates (Priority: Medium) ✅

### 4.1 SOLID Compliance ✅
- [x] Document SOLID principles in CLAUDE.md with examples
- [x] Add linting rules for single responsibility
- [ ] Review and refactor any violations found

### 4.2 SSOT Enforcement ✅
- [x] Document canonical sources for all concerns
- [ ] Identify duplicate logic in codebase
- [ ] Create shared utilities for common patterns

## Validation

- [ ] Run `openspec validate complete-e2e-tdd-evolution --strict`
- [ ] All E2E tests pass locally
- [ ] All E2E tests pass in CI
- [ ] Coverage meets threshold (>= 80%)
- [ ] No test flakiness (3 consecutive green runs)

## Dependencies

- Phase 2 depends on Phase 1 completion ✅
- Phase 3 and 4 can run in parallel with Phase 2 ✅
- Final validation requires all phases complete

## Implementation Summary

### Files Created:
- `frontend/tests/e2e/pages/LandingPage.ts` - Page Object for landing page
- `frontend/tests/e2e/landing-page.spec.ts` - Landing page E2E tests
- `frontend/tests/e2e/protected-routes.spec.ts` - Protected route tests
- `frontend/tests/e2e/navigation.spec.ts` - Wildcard route tests
- `frontend/tests/e2e/user-journey.spec.ts` - User journey tests
- `frontend/tests/e2e/error-boundaries.spec.ts` - Error boundary tests
- `frontend/tests/e2e/navigation-flows.spec.ts` - Navigation flow tests

### Files Updated:
- `frontend/tests/e2e/login-flow.spec.ts` - Extended with login placeholder tests
- `frontend/CLAUDE.md` - Added TDD workflow, templates, SOLID examples, SSOT canonical sources
