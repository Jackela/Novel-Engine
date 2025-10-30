---

description: "Task list for QA Pipeline Hardening"
---

# Tasks: QA Pipeline Hardening

**Input**: Design documents from `/specs/003-qa-hardening/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Run formatting/lint suite and regression pytest per user stories; Playwright/browser installs are part of setup.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare tooling and environment baselines before repository-wide formatting and test fixes.

- [ ] T001 Verify prerequisite tooling (Python 3.11+, docker, act, playwright) documented in docs/observability/charter.md and quickstart.md
- [ ] T002 [P] Bootstrap QA virtual environment script in scripts/validate_ci_locally.sh
- [ ] T003 [P] Ensure playwright browsers installed via python3 -m playwright install # requirements/Tooling
- [ ] T004 Create temporary formatting branch snapshot for comparison (git worktree add ./worktrees/qa-format)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish formatting/lint configuration and shared scripts prior to story execution.

- [ ] T005 Consolidate formatter configuration in pyproject.toml (black/isort) and .flake8
- [ ] T006 Update .pre-commit-config.yaml (if present) or create to run black/isort/flake8/mypy
- [ ] T007 [P] Generate formatting exclusions list (e.g., migrations, third-party) in scripts/format_exclude.txt
- [ ] T008 Align .gitignore/.eslintignore/.terraformignore with formatting/lint outputs (cache, reports)
- [ ] T009 Document QA prerequisites in README.md and docs/qa/contract-validation.md

---

## Phase 3: User Story 1 - Enforce Repository Formatting Baseline (Priority: P1) 🎯 MVP

**Goal**: Repository conforms to black/isort/flake8/mypy policies and passes code-quality job.

**Independent Test**: Run `python3 -m black --check src tests ai_testing` and `python3 -m isort --check-only ...`, plus `python3 -m flake8` and `python3 -m mypy src` with zero failures.

### Tests for User Story 1

- [ ] T010 [P] [US1] Run formatting dry-run (black --check, isort --check) to capture initial diff report (store under reports/qa/formatting-drift.txt)

### Implementation for User Story 1

- [ ] T011 [US1] Apply black formatting to src/, tests/, ai_testing/, scripts/
- [ ] T012 [US1] Apply isort (profile=black) to src/, tests/, ai_testing/
- [ ] T013 [US1] Resolve flake8 violations across repository (target paths in reports/qa/flake8.log)
- [ ] T014 [US1] Fix mypy errors in src/ (add type hints, adjust config)
- [ ] T015 [US1] Update .github/workflows/quality_assurance.yml to call shared formatter script and adjust timeout to 25m
- [ ] T016 [US1] Commit formatting results snapshot in reports/qa/formatting-summary.md

**Checkpoint**: Black/isort/flake8/mypy run clean locally and in CI.

---

## Phase 4: User Story 2 - Restore Core Test Suite Stability (Priority: P1)

**Goal**: Critical regression tests (especially turn orchestration) pass consistently.

**Independent Test**: `python3 -m pytest -m "not requires_services" --tb=short` executes without unexpected failures; skip/xfail documented.

### Tests for User Story 2

- [ ] T017 [P] [US2] Capture current pytest failure logs for TestTurnOrchestrationE2E into reports/qa/test_failures_before.log

### Implementation for User Story 2

- [ ] T018 [US2] Create deterministic fixtures/mocks in tests/integration/test_e2e_turn_orchestration.py (phase tracker)
- [ ] T019 [US2] Replace return-based assertions with explicit asserts in tests/integration_validation_test.py and phase1_validation_test.py
- [ ] T020 [US2] Register custom pytest markers in pytest.ini (markers: requires_services, character) # config/pytest.ini
- [ ] T021 [US2] Update tests/integration/api/test_simple.py to use assert statements instead of returns
- [ ] T022 [US2] Re-run pytest -m "not requires_services" and store results in reports/qa/pytest-after.log
- [ ] T023 [US2] Document skip/xfail rationales in docs/qa/regression-test-catalog.md

**Checkpoint**: Regression suite passes (or intentional skips documented).

---

## Phase 5: User Story 3 - Codify QA Tooling & CI Integration (Priority: P2)

**Goal**: Local validation script and act workflows aligned with new QA process.

**Independent Test**: Run `./scripts/validate_ci_locally.sh` on clean env; run `act --secret-file .secrets -W .github/workflows/quality_assurance.yml`.

### Tests for User Story 3

- [ ] T024 [P] [US3] Execute scripts/validate_ci_locally.sh on clean container (CI or devcontainer) and capture logs in reports/qa/validate-ci.log
- [ ] T025 [P] [US3] Run act QA workflow; capture job summary in reports/qa/act-run.log

### Implementation for User Story 3

- [ ] T026 [US3] Enhance scripts/validate_ci_locally.sh: create .venv-ci, install requirements with fallback `--break-system-packages`, run format+tests sequentially
- [ ] T027 [US3] Update quickstart/README with QA workflow steps (act usage, dependency install)
- [ ] T028 [US3] Add caching strategy to .github/workflows/quality_assurance.yml (`actions/cache` for .venv-ci or pip cache)
- [ ] T029 [US3] Provide troubleshooting guide in docs/qa/troubleshooting.md (timeouts, docker image pulls)
- [ ] T030 [US3] Ensure Playwright installation step added to .github/workflows/quality_assurance.yml (playwright install chromium)

**Checkpoint**: Local QA script and act workflow run successfully with updated documentation.

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Final documentation updates, communication, and cleanup.

- [ ] T031 [P] Update docs/comms/refactor-briefing.md with QA hardening summary and impact
- [ ] T032 [P] Refresh docs/changelog/2025-10.md with QA hardening entry (formatting, test fixes)
- [ ] T033 [Training] Update onboarding guide (docs/onboarding/guide.md) to reference new QA tooling
- [ ] T034 [Quality Assurance] Final rerun logging to reports/qa/final-validation.log using scripts/validate_ci_locally.sh --final
- [ ] T035 Clean up temporary worktree and caches (worktrees/qa-format, coverage/htmlcov, __pycache__)

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup → Foundational → US1 → US2 → US3 → Polish
- US2 depends on formatting baseline (US1) to avoid churn; US3 depends on both for accurate tooling scripts.

### User Story Dependencies

- US1 (formatting baseline) must complete before US2 & US3 to prevent conflicting diffs.
- US2 needs stable formatting to modify tests cleanly; US3 depends on scripts referencing updated workflows.

### Within Each User Story

- Follow order: tests capture → implementation changes → rerun validations.
- Tasks marked [P] can run concurrently if they target different files/areas.

### Parallel Example: User Story 1

```bash
# In separate shells
python3 -m black src tests ai_testing &
python3 -m isort src tests ai_testing &
wait
python3 -m flake8 src tests ai_testing
python3 -m mypy src
```

---

## Implementation Strategy

1. **MVP (US1)**: Establish formatting/lint baseline and CI adjustments.
2. **Stabilize Tests (US2)**: Fix failing regression tests, document skips.
3. **Tooling Integration (US3)**: Update scripts/act workflows and documentation.
4. **Polish**: Communicate changes, update onboarding, final validation.
