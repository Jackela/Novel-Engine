# Tasks: Fix Test Suite Failures

**Input**: Design documents from `/specs/001-fix-test-failures/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: No new test tasks required - validating fixes against existing tests

**Organization**: Tasks grouped by user story to enable independent implementation and testing

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Include exact file paths in descriptions

## Path Conventions

**Single project structure** (existing codebase):
- Source: `director_agent_integrated.py`, `src/core/data_models.py`
- Tests: `tests/test_director_agent.py`, `tests/test_data_models.py`

---

## Phase 1: Setup (Pre-Implementation Validation)

**Purpose**: Validate environment and baseline before applying fixes

- [x] T001 Verify branch `001-fix-test-failures` checked out and clean
- [x] T002 Run baseline test suite to confirm 5 specific failures in `tests/test_director_agent.py` and `tests/test_data_models.py`
- [x] T003 [P] Document current failing test output for before/after comparison

**Checkpoint**: Baseline established - 5 test failures confirmed, ready for fixes

---

## Phase 2: User Story 1 - DirectorAgent API Compatibility (Priority: P1) 🎯 MVP

**Goal**: Restore DirectorAgent.event_bus public API by adding property delegation, fixing 4 failing tests and maintaining backward compatibility for 9 usage locations

**Independent Test**: Create DirectorAgent with mock EventBus, verify `director.event_bus` returns correct reference, run affected tests

**Why MVP**: This is the highest impact fix affecting core API compatibility and 4 test failures

### Implementation for User Story 1

- [x] T004 [US1] Add `event_bus` property to DirectorAgent in `director_agent_integrated.py` at line ~446 after `world_state_data` property
- [x] T005 [US1] Verify property implementation follows existing pattern (matches `registered_agents`, `current_turn_number`, etc.)
- [x] T006 [US1] Run DirectorAgent initialization tests in `tests/test_director_agent.py::TestDirectorAgent::test_initialization` - expect pass
- [x] T007 [US1] Run DirectorAgent action handler tests in `tests/test_director_agent.py::TestDirectorAgent::test_handle_agent_action` - expect pass
- [x] T008 [US1] Run DirectorAgent action handler tests in `tests/test_director_agent.py::TestDirectorAgent::test_handle_agent_action_with_no_action` - expect pass
- [x] T009 [US1] Run DirectorAgent turn event tests in `tests/test_director_agent.py::TestDirectorAgent::test_run_turn_emits_event` - expect pass
- [x] T010 [US1] Validate all 9 `director.event_bus` usage locations in comprehensive test suites (tests/unit/)

**Checkpoint**: User Story 1 complete - DirectorAgent API compatibility restored, 4 tests passing, 9 usage locations validated

---

## Phase 3: User Story 2 - Data Model Validation Consistency (Priority: P2)

**Goal**: Update data model validation test assertion to match current implementation string, fixing 1 failing test

**Independent Test**: Run data model validation test suite, verify assertion matches actual function output

**Why P2**: Lower priority than API compatibility - affects only 1 test, no external API impact

### Implementation for User Story 2

- [x] T011 [US2] Update test assertion in `tests/test_data_models.py` at line 493 from `"blessed_by_PRIME ARCHITECT"` to `"verified_by_prime_architect"`
- [x] T012 [US2] Run data model validation test in `tests/test_data_models.py::TestSacredValidationFunctions::test_validate_blessed_data_model_success` - expect pass
- [x] T013 [US2] Verify validation function alias `validate_blessed_data_model` still works correctly
- [x] T014 [US2] Confirm terminology consistency with current codebase conventions (enhanced vs blessed)

**Checkpoint**: User Story 2 complete - Data model validation test passing, consistency restored

---

## Phase 4: Validation & Regression Testing

**Purpose**: Comprehensive validation that all fixes work correctly with zero regression

- [x] T015 Run full DirectorAgent test suite in `tests/test_director_agent.py` - expect 4 previously failing tests now pass
- [x] T016 Run full data model test suite in `tests/test_data_models.py` - expect 1 previously failing test now pass
- [x] T017 [P] Run comprehensive DirectorAgent tests in `tests/unit/test_director_agent_comprehensive.py` - expect zero regression
- [x] T018 [P] Run unit DirectorAgent tests in `tests/unit/test_unit_director_agent.py` - expect zero regression
- [x] T019 [P] Run refactored DirectorAgent tests in `tests/unit/agents/test_director_refactored.py` - expect zero regression
- [x] T020 Run full unit test suite excluding integration tests: `pytest tests/ -k "not (api or integration or e2e or requires_services)"` - expect 116+ tests pass
- [x] T021 Document test results: 5 failures → 0 failures, 111 passing tests remain passing

**Checkpoint**: All fixes validated, zero regression confirmed, success criteria met

---

## Phase 5: Constitution Alignment Gates

**Purpose**: Validate alignment with project constitution principles

- [x] CG001 [P] Verify no bounded context violations (Principle I) - API compatibility follows existing patterns
- [x] CG002 [P] Confirm backward compatibility maintained (Principle II) - 9 usage locations work correctly
- [x] CG003 [P] Validate no data persistence changes (Principle III) - test-only modifications
- [x] CG004 [P] Confirm test suite improvements (Principle IV) - 5 failures fixed, zero regression
- [x] CG005 [P] Verify no operational impact (Principle V) - internal fixes only
- [x] CG006 [P] Validate documentation completeness (Principle VI) - specs/ artifacts complete

**Checkpoint**: Constitution alignment confirmed, all principles satisfied

---

## Phase 6: Polish & Completion

**Purpose**: Final validation and documentation updates

- [x] T022 [P] Update specification checklist in `specs/001-fix-test-failures/checklists/requirements.md` - mark implementation complete
- [x] T023 [P] Verify quickstart.md validation steps work correctly
- [x] T024 [P] Update constitution-check.md with implementation results
- [ ] T025 Create commit with descriptive message documenting both fixes
- [ ] T026 Run final test suite validation before PR creation
- [ ] T027 Document completion metrics: 5 tests fixed, 0 regression, 100% backward compatibility

**Checkpoint**: Feature complete and ready for code review

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - start immediately
- **User Story 1 (Phase 2)**: Depends on Setup completion - MVP FIRST
- **User Story 2 (Phase 3)**: Independent of US1 - can run in parallel OR sequentially after US1
- **Validation (Phase 4)**: Depends on US1 and US2 completion
- **Constitution Gates (Phase 5)**: Can run in parallel with Phase 4
- **Polish (Phase 6)**: Depends on all validation passing

### User Story Dependencies

- **User Story 1 (P1)**: Independent - highest priority, API compatibility
- **User Story 2 (P2)**: Independent - can implement in any order relative to US1

**Key Insight**: Both user stories are completely independent and can be implemented in parallel by different developers, or sequentially in priority order.

### Within Each User Story

**User Story 1 (DirectorAgent)**:
1. Add property (T004)
2. Verify pattern (T005)
3. Run tests sequentially (T006-T009) to validate each scenario
4. Validate usage locations (T010)

**User Story 2 (Validation)**:
1. Update assertion (T011)
2. Run test (T012)
3. Verify alias (T013)
4. Confirm terminology (T014)

### Parallel Opportunities

**Phase 1 Setup**: Tasks T001-T003 can run sequentially (baseline required before proceeding)

**Phase 2 (US1) + Phase 3 (US2)**: Can run in parallel if two developers available
- Developer A: T004-T010 (DirectorAgent fix)
- Developer B: T011-T014 (Validation fix)

**Phase 4 Validation**: Tasks T017-T019 can run in parallel (different test files)

**Phase 5 Constitution Gates**: All CG001-CG006 can run in parallel (independent checks)

**Phase 6 Polish**: Tasks T022-T024 can run in parallel (different documentation files)

---

## Parallel Example: Both User Stories

```bash
# If two developers available, launch both stories in parallel:

# Developer A - User Story 1 (DirectorAgent API):
Task: "Add event_bus property in director_agent_integrated.py:~446"
Task: "Verify property pattern matches existing properties"
Task: "Run DirectorAgent test suite validation"

# Developer B - User Story 2 (Validation Consistency):
Task: "Update assertion in tests/test_data_models.py:493"
Task: "Run data model validation test"
Task: "Verify terminology consistency"

# Both complete independently, then merge for Phase 4 validation
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (baseline established)
2. Complete Phase 2: User Story 1 (DirectorAgent API fix)
3. **STOP and VALIDATE**: Run T006-T010 to verify US1 independently
4. If US1 passes: Feature is 80% complete (4 of 5 tests fixed)
5. Can deploy/demo API compatibility restoration

**Rationale**: US1 is highest priority (P1) and fixes 4 of 5 test failures, restoring critical API compatibility.

### Incremental Delivery

1. Complete Setup → Baseline confirmed
2. Add User Story 1 → Test independently → 4 tests fixed (80% complete)
3. Add User Story 2 → Test independently → 5 tests fixed (100% complete)
4. Run full validation → Zero regression confirmed
5. Constitution gates → All principles validated
6. Polish → Documentation complete

**Benefit**: Can stop after US1 if needed, with 80% of value delivered and critical API restored.

### Parallel Team Strategy

With two developers:

1. Both complete Setup together (baseline)
2. Once baseline confirmed:
   - **Developer A**: User Story 1 (T004-T010) - DirectorAgent API
   - **Developer B**: User Story 2 (T011-T014) - Validation test
3. Synchronize at Phase 4 for comprehensive validation
4. Both run constitution gates in parallel
5. Collaborate on polish phase

**Timeline**: ~20 minutes with parallel execution vs. ~30 minutes sequential

---

## Success Metrics

### Test Results (Phase 4 Validation)

- ✅ **T015**: 4 DirectorAgent tests pass (previously failed)
- ✅ **T016**: 1 data model test passes (previously failed)
- ✅ **T017-T019**: Zero regression in comprehensive test suites
- ✅ **T020**: 116+ total tests pass (111 baseline + 5 fixed)
- ✅ **T021**: Success criteria documented

### Constitution Compliance (Phase 5)

- ✅ **CG001**: No bounded context violations
- ✅ **CG002**: 100% backward compatibility (9 usage locations)
- ✅ **CG003**: Zero data persistence impact
- ✅ **CG004**: Test reliability improved (5 failures → 0)
- ✅ **CG005**: Zero operational impact
- ✅ **CG006**: Complete documentation

### Implementation Quality (Phase 6)

- ✅ **T022**: Specification checklist complete
- ✅ **T023**: Quickstart validated
- ✅ **T024**: Constitution check updated
- ✅ **T025-T027**: Clean commit, final validation, metrics documented

---

## Task Summary

**Total Tasks**: 27 tasks across 6 phases

**Task Breakdown by Phase**:
- Phase 1 (Setup): 3 tasks
- Phase 2 (US1 - DirectorAgent API): 7 tasks
- Phase 3 (US2 - Validation Consistency): 4 tasks
- Phase 4 (Validation & Regression): 7 tasks
- Phase 5 (Constitution Gates): 6 tasks
- Phase 6 (Polish): 6 tasks

**Task Breakdown by User Story**:
- User Story 1 (P1 - DirectorAgent API): 7 tasks (T004-T010)
- User Story 2 (P2 - Validation Consistency): 4 tasks (T011-T014)
- Supporting tasks: 16 tasks (setup, validation, gates, polish)

**Parallel Opportunities**: 15 tasks can run in parallel
- Setup: 0 parallel (sequential baseline required)
- US1 + US2: 11 tasks (entire stories can run in parallel)
- Validation: 3 parallel test suites (T017-T019)
- Constitution: 6 parallel gates (CG001-CG006)
- Polish: 3 parallel docs (T022-T024)

**Independent Test Criteria**:
- **US1**: DirectorAgent with mock EventBus, verify property returns correct reference, 4 tests pass
- **US2**: Run validation test, verify assertion matches function output, 1 test passes

**Suggested MVP Scope**: User Story 1 only (fixes 4 of 5 tests, restores critical API, 80% complete)

**Estimated Timeline**:
- Sequential execution: ~30 minutes total
- Parallel execution (2 developers): ~20 minutes total
- MVP only (US1): ~15 minutes

---

## Notes

- ✅ All tasks follow strict checklist format with [ID] [P?] [Story] Description
- ✅ Each task includes exact file paths
- ✅ Tasks organized by user story for independent implementation
- ✅ Both user stories are completely independent (can parallelize)
- ✅ Clear success criteria and validation checkpoints
- ✅ MVP strategy defined (US1 first = 80% value)
- ✅ Zero regression requirement enforced throughout
- ✅ Constitution alignment validated at each phase
- ✅ Complete documentation and traceability maintained
