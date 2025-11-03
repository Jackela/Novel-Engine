# Implementation Plan: Fix Test Suite Failures

**Branch**: `001-fix-test-failures` | **Date**: 2025-11-03 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/001-fix-test-failures/spec.md`

## Summary

Fix 5 failing test cases by restoring DirectorAgent API backward compatibility and updating data model validation test expectations. The DirectorAgent was recently refactored to use composition pattern, breaking the public `event_bus` API across 9 usage locations. Additionally, validation function renaming changed the validation response string, causing test assertion mismatches. This plan adds a property delegation for `event_bus` (following existing patterns) and updates test assertions to match current implementation.

## Technical Context

**Language/Version**: Python 3.12.6  
**Primary Dependencies**: pytest 8.4.2, unittest (stdlib)  
**Storage**: N/A - No persistence changes  
**Testing**: pytest with unittest.TestCase base classes  
**Target Platform**: Windows/Linux development environments  
**Project Type**: Single project (Python library/framework)  
**Performance Goals**: N/A - Test fixes only, no runtime performance impact  
**Constraints**: Must maintain 100% backward compatibility for DirectorAgent API, zero regression in 111 passing tests  
**Scale/Scope**: 5 test fixes, 2 file modifications (director_agent_integrated.py, test_data_models.py)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Domain-Driven Narrative Core**: ✅ No bounded context changes - maintains existing agent coordination interfaces, no ADR updates required
- **Contract-First Experience APIs**: ✅ Preserves public API contract for DirectorAgent.event_bus, no consumer notifications needed (internal test fixes)
- **Data Stewardship & Persistence Discipline**: ✅ No migrations, storage, or data changes - test expectations only
- **Quality Engineering & Testing Discipline**: ✅ Fixes 5 failing tests, maintains existing pytest/unittest suites, validates backward compatibility, zero regression requirement enforced
- **Operability, Security & Reliability**: ✅ No telemetry, feature flags, or runbook changes - internal test infrastructure only
- **Documentation & Knowledge Stewardship**: ✅ No documentation updates required - follows existing property delegation pattern, changes are self-documenting through code
- Constitution Gate Workbook Run Date: 2025-11-03 (internal test fixes, minimal governance overhead)

**Gate Result**: ✅ PASSED - All principles satisfied, no violations

## Project Structure

### Documentation (this feature)

```text
specs/001-fix-test-failures/
├── spec.md              # Feature specification
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (technical investigation)
├── checklists/
│   └── requirements.md  # Specification quality validation
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT yet created)
```

### Source Code (repository root)

```text
# Existing structure - no new files created
director_agent_integrated.py    # Add event_bus property
src/core/data_models.py         # No changes (validation string is correct)
tests/test_data_models.py       # Update test assertion
tests/test_director_agent.py    # Validates fixes (existing tests)

# Full test structure (existing)
tests/
├── unit/                       # Unit test suites
│   ├── test_director_agent_comprehensive.py
│   ├── test_unit_director_agent.py
│   └── agents/
│       └── test_director_refactored.py
├── test_director_agent.py      # Primary test file to validate
└── test_data_models.py         # Test file requiring assertion update
```

**Structure Decision**: Single project structure with existing test organization. No new directories or files required - only modifications to 2 existing files (director_agent_integrated.py for property addition, test_data_models.py for assertion update).

## Complexity Tracking

> **No violations** - All constitution principles satisfied, no justification required.

## Phase 0: Research & Technical Investigation

### Research Goals

1. **DirectorAgent Composition Pattern Analysis**
   - Document the refactoring that introduced composition (DirectorAgentBase)
   - Identify all existing property delegation patterns
   - Map all 9 usage locations of `director.event_bus` API

2. **Property Delegation Best Practices**
   - Review Python property decorator patterns
   - Validate approach against existing code (registered_agents, current_turn_number, etc.)
   - Confirm zero performance overhead for property access

3. **Validation Function Renaming Analysis**
   - Trace the validate_blessed_data_model → validate_enhanced_data_model refactoring
   - Confirm alias exists for backward compatibility
   - Document the validation string change rationale

4. **Test Infrastructure Compatibility**
   - Verify pytest and unittest.mock compatibility
   - Confirm test isolation patterns
   - Validate that property access works correctly with Mock(spec=EventBus)

### Research Outputs

Document findings in `research.md`:
- Composition pattern rationale and implementation details
- Property delegation implementation approach with code examples
- Test modification strategy with minimal change principle
- Validation of zero regression risk

## Phase 1: Design & Implementation Strategy

### Design Decisions

**Decision 1: Property Delegation Pattern**
- **Rationale**: Follows existing patterns (registered_agents, current_turn_number, simulation_start_time, total_actions_processed, error_count, campaign_log_path, world_state_file_path, world_state_data)
- **Implementation**: Add `@property` decorator returning `self.base.event_bus`
- **Location**: director_agent_integrated.py, line ~445 (after world_state_data property)

**Decision 2: Test Assertion Update**
- **Rationale**: Update test to match current implementation (intentional refactoring)
- **Implementation**: Change assertion from `"blessed_by_PRIME ARCHITECT"` to `"verified_by_prime_architect"`
- **Location**: tests/test_data_models.py, line 493

**Decision 3: No Additional Changes**
- **Rationale**: Minimal change principle - only fix identified issues
- **Scope**: Do not refactor other methods, add new tests, or modify validation logic

### Implementation Components

**Component 1: DirectorAgent Property Addition**
```python
@property
def event_bus(self) -> EventBus:
    """Get event bus instance."""
    return self.base.event_bus
```

**Component 2: Test Assertion Update**
```python
# Change from:
assert result.data["validation"] == "blessed_by_PRIME ARCHITECT"
# To:
assert result.data["validation"] == "verified_by_prime_architect"
```

### Testing Strategy

**Test Validation Plan**:
1. Run `tests/test_director_agent.py` - expect 4 failures → 0 failures
2. Run `tests/test_data_models.py::TestSacredValidationFunctions::test_validate_blessed_data_model_success` - expect 1 failure → 0 failures
3. Run full test suite excluding integration tests - expect 111 passing tests to remain passing (zero regression)
4. Verify all 9 usage locations of `director.event_bus` work correctly

**Success Metrics**:
- 5 failing tests → 0 failing tests (100% fix rate)
- 111 passing tests remain passing (0% regression rate)
- All 9 `director.event_bus` usage locations maintain compatibility

### Data Model

**No data model changes required** - this feature only modifies code interfaces and test expectations.

### API Contracts

**No contract changes required** - internal API compatibility restoration, no external contracts affected.

## Phase 2: Task Breakdown (generated by /speckit.tasks)

*This section will be populated by the `/speckit.tasks` command, which breaks down implementation into specific tasks aligned with user stories from the specification.*

**Expected tasks**:
- Task 1: Add event_bus property to DirectorAgent (User Story 1, P1)
- Task 2: Update data model validation test assertion (User Story 2, P2)
- Task 3: Run test suite validation and verify zero regression
- Task 4: Update checklist and mark feature complete

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Property access breaks existing mock patterns | High | Low | Validate with Mock(spec=EventBus) in tests |
| Regression in passing tests | High | Very Low | Run full test suite before/after, zero tolerance for regression |
| Performance overhead from property access | Low | Very Low | Property delegation has zero overhead in Python |
| Breaking other DirectorAgent APIs | Medium | Very Low | Follow exact pattern used by 8 existing properties |

## Dependencies & Blockers

**Internal Dependencies**:
- ✅ DirectorAgent composition architecture (stable, no changes needed)
- ✅ EventBus implementation (stable, no changes needed)
- ✅ Test infrastructure (pytest 8.4.2, unittest)

**External Dependencies**: None

**Blockers**: None identified

## Validation Criteria

**Code Quality Gates**:
- ✅ Property implementation follows existing patterns exactly
- ✅ No new complexity introduced (simple delegation)
- ✅ Test assertions updated to match current implementation
- ✅ Zero style/linting violations

**Testing Gates**:
- ✅ All 5 identified test failures resolved
- ✅ Zero regression in 111 passing tests
- ✅ All 9 `director.event_bus` usage locations validated
- ✅ Test suite completes without syntax errors or collection failures

**Constitution Gates**:
- ✅ No bounded context violations
- ✅ Backward compatibility maintained (100%)
- ✅ No data/storage changes
- ✅ Test coverage maintained
- ✅ No operational impact

## Sign-off

**Plan Status**: ✅ Complete - Ready for Phase 0 Research  
**Constitution Check**: ✅ Passed all principles  
**Next Command**: `/speckit.tasks` to generate detailed task breakdown

**Notes**:
- Minimal change approach reduces risk
- Follows established patterns throughout
- Zero regression tolerance enforced
- Ready for immediate implementation after research phase
