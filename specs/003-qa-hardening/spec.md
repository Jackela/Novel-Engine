# Feature Specification: QA Pipeline Hardening

**Feature Branch**: `003-qa-hardening`  
**Created**: 2025-10-29
**Status**: Draft  
**Input**: User description: "Stabilize QA pipeline: formatting cleanup, fix failing integration tests, ensure linters pass."

## User Scenarios & Testing *(mandatory)*

For each story, state the bounded context it touches and note any ports/adapters or anti-corruption layers affected.

### User Story 1 - Enforce Repository Formatting Baseline (Priority: P1)
**Bounded Contexts**: Platform Operations (governance tooling), Simulation Orchestration/Narrative Delivery (source modules impacted by formatting).

As the QA gatekeeper, I need a repeatable formatting/linting workflow (Black, isort, Flake8, MyPy) so that the `code-quality` GitHub Actions job passes without manual intervention.

**Why this priority**: Current formatting drift causes the pipeline to fail and blocks all CI feedback.

**Independent Test**: Run formatting & lint suite locally (`black --check`, `isort --check`, `flake8`, `mypy`) and confirm the GitHub Actions `code-quality` job succeeds.

**Acceptance Scenarios**:
1. **Given** mixed formatting across modules, **When** the formatting script runs, **Then** all Python files under `src/`, `tests/`, and `ai_testing/` conform to Black/isort rules with no syntax errors.
2. **Given** the repository after cleanup, **When** `black --check src tests ai_testing` executes in CI, **Then** it exits with status 0.

---

### User Story 2 - Restore Core Test Suite Stability (Priority: P1)
**Bounded Contexts**: Simulation Orchestration, Platform Operations.

As the QA engineer, I need the failing integration test (`TestTurnOrchestrationE2E`) and similar high-value tests to pass reliably so the `test-suite` job can succeed.

**Why this priority**: Regression pipeline currently fails due to the turn orchestration test returning zero phases.

**Independent Test**: Run `pytest -m "not requires_services"` locally; confirm the previously failing integration tests pass, and document any intentional skips.

**Acceptance Scenarios**:
1. **Given** the regression suite, **When** `pytest -m "not requires_services"` runs, **Then** `TestTurnOrchestrationE2E::test_complete_turn_orchestration_e2e` passes without manual fixtures.
2. **Given** optional heavy tests, **When** CI executes with updated markers, **Then** non-actionable warnings (`PytestReturnNotNoneWarning`, unknown marks) are eliminated or justified via documented skip/xfail.

---

### User Story 3 - Codify QA Tooling & CI Integration (Priority: P2)
**Bounded Contexts**: Platform Operations.

As the DevOps engineer, I want automation scripts (`scripts/validate_ci_locally.sh`, act config) and documentation aligned with the new workflow so contributors can reproduce QA locally.

**Why this priority**: Without tooling updates, developers repeatedly hit missing pip/packages, act timeouts, or silent lint failures.

**Independent Test**: Run `./scripts/validate_ci_locally.sh` on a clean Linux environment; run `act --secret-file .secrets -W .github/workflows/quality_assurance.yml` to completion.

**Acceptance Scenarios**:
1. **Given** a fresh Linux env with documented prerequisites, **When** `./scripts/validate_ci_locally.sh` runs, **Then** it installs requirements in a virtualenv and finishes with green status.
2. **Given** developers following the quickstart, **When** they run `act` for the QA workflow, **Then** the job completes without hitting missing-tool timeouts (or provides clear instructions for Docker image size limits).

---

### Edge Cases
- What happens when repository contributors are on Windows and run formatting (line endings)?  
- How does the pipeline handle large codebases that exceed default `act` execution time?  
- What is the fallback if Playwright browsers are unavailable or tests require external services?  
- How are skipped/xfail tests documented to avoid masking regressions?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001 (Context: Platform Operations, Contract: QA Tooling)**: System MUST provide a scripted formatter/linter workflow (Black, isort, Flake8, MyPy) that exits successfully in CI and locally.  
- **FR-002 (Context: Simulation Orchestration, Contract: Pytest Suite)**: System MUST ensure targeted integration/unit tests (including `TestTurnOrchestrationE2E`) pass with documented fixtures or skip rationale.  
- **FR-003 (Context: Platform Operations, Contract: CLI)**: System MUST upgrade `scripts/validate_ci_locally.sh` to bootstrap dependencies via virtualenv and run QA checks end-to-end.  
- **FR-004 (Context: Platform Operations, Contract: GitHub Actions)**: CI workflows MUST be updated to reference new lint/test scripts and manage long-running jobs gracefully (timeouts, matrix strategy, caching).  
- **FR-005 (Context: Platform Operations, Contract: Documentation)**: Documentation MUST instruct engineers on prerequisites (Python 3.11+, Playwright installation, Docker/act) and link to formatting/test commands.

### Key Entities
- **Formatting Policy**: Defines Black/isort configurations, exclusion lists, and enforcement scripts.  
- **QA Toolchain Config**: Captures Python virtualenv settings, Playwright installation instructions, act usage, and caching strategy.  
- **Regression Test Catalog**: Maps critical tests, skip/xfail rationale, and maintenance owners.

### Non-Functional & Operability Requirements

- **NFR-001 (SLO)**: QA workflows (code-quality + test-suite) must complete within 20 minutes on GitHub Actions.  
- **NFR-002 (Observability)**: Lint/test scripts need consistent logging (start/end markers, failure summaries) to ease debugging.  
- **NFR-003 (Security)**: QA scripts must avoid installing system packages with elevated privileges; dependencies pinned to avoid supply-chain regressions.  
- **NFR-004 (Resiliency)**: Provide a retry path or documentation if act pulls large Docker images or hits network failures.  
- **NFR-005 (Deployment/Rollout)**: Rollout plan must run formatting in staging branch first, communicate impact to contributors, and require sign-off before enforcing in protected branches.

## Success Criteria *(mandatory)*

- **SC-001**: `black --check`, `isort --check-only`, `flake8`, and `mypy` run cleanly on CI and local script.  
- **SC-002**: `pytest -m "not requires_services"` passes without unexpected failures; known skips/xfails documented.  
- **SC-003**: `./scripts/validate_ci_locally.sh` completes successfully on a clean Linux environment (documented prerequisites).  
- **SC-004**: `act --secret-file .secrets -W .github/workflows/quality_assurance.yml` completes without timeout or missing-tool errors using the documented configuration.  
- **SC-005**: Documentation/README updated so new contributors can reproduce QA pipeline in ≤10 steps.
