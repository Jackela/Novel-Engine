# Feature Specification: Fix Test Suite Failures

**Feature Branch**: `001-fix-test-failures`  
**Created**: 2025-11-03  
**Status**: Draft  
**Input**: User description: "Solve all issues found by test suites."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - DirectorAgent API Compatibility (Priority: P1)

Developers using the DirectorAgent class need to access the event_bus attribute through the public API to subscribe to events and coordinate agent communication. After a recent refactoring to modular architecture, this attribute is no longer directly accessible, breaking 9 existing test cases and potentially breaking external code that depends on this API.

**Why this priority**: This is the highest impact issue affecting 4 failing tests and potentially breaking backward compatibility for any code using the DirectorAgent API. Without this fix, the core agent coordination system is unusable.

**Independent Test**: Can be fully tested by instantiating DirectorAgent with a mock EventBus and verifying `director.event_bus` returns the correct reference. Delivers immediate API compatibility restoration.

**Acceptance Scenarios**:

1. **Given** a DirectorAgent instance created with an EventBus, **When** accessing `director.event_bus`, **Then** the original EventBus reference is returned
2. **Given** existing test code expecting `director.event_bus`, **When** tests run, **Then** all DirectorAgent initialization tests pass
3. **Given** multiple components accessing `director.event_bus`, **When** they subscribe to events, **Then** event subscriptions work correctly
4. **Given** the DirectorAgent composition pattern with internal `base.event_bus`, **When** accessing via public property, **Then** proper encapsulation is maintained

---

### User Story 2 - Data Model Validation Consistency (Priority: P2)

Developers testing data model validation need consistent validation response strings that match the current function naming conventions. The validation function was renamed from `validate_blessed_data_model` to `validate_enhanced_data_model`, and the validation response changed from `"blessed_by_PRIME ARCHITECT"` to `"verified_by_prime_architect"`, but one test still expects the old string.

**Why this priority**: This affects 1 test failure and represents a minor inconsistency after intentional refactoring. Lower priority than P1 because it doesn't break external APIs, only internal test expectations.

**Independent Test**: Can be fully tested by running the data model validation test suite and verifying the assertion matches the actual validation response string. Delivers test consistency with current implementation.

**Acceptance Scenarios**:

1. **Given** a valid MemoryItem instance, **When** validating with `validate_blessed_data_model`, **Then** validation response contains `"verified_by_prime_architect"`
2. **Given** the validation function alias exists for backward compatibility, **When** tests run, **Then** test expectations match actual function behavior
3. **Given** the intentional refactoring from "blessed" to "enhanced" naming, **When** reviewing test assertions, **Then** old terminology is updated to match new conventions

---

### Edge Cases

- What happens when DirectorAgent is accessed by code expecting the old direct attribute (not property)?
- What happens when validation tests check for specific string values after refactoring?
- How does the system handle backward compatibility for external code using these APIs?
- What happens if future refactoring changes internal composition but needs to maintain public API?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: DirectorAgent MUST expose `event_bus` attribute through a public property that delegates to internal composition
- **FR-002**: DirectorAgent property access MUST return the exact EventBus instance provided during initialization
- **FR-003**: Test suite MUST validate that `director.event_bus` returns the correct EventBus reference
- **FR-004**: Data model validation test MUST expect validation response `"verified_by_prime_architect"` to match current implementation
- **FR-005**: All existing DirectorAgent tests MUST pass after API compatibility is restored
- **FR-006**: All data model validation tests MUST pass after string expectations are updated
- **FR-007**: System MUST maintain backward compatibility pattern consistent with existing properties (registered_agents, current_turn_number, etc.)

### Key Entities

- **DirectorAgent**: Main orchestration class that coordinates agents through EventBus, refactored to use composition pattern with internal base component
- **EventBus**: Event coordination system that agents use for decoupled communication
- **ValidationResponse**: Data structure returned by validation functions containing success status and validation metadata

## Constitution Alignment *(mandatory)*

- **Domain-Driven Narrative Core**: Maintains agent coordination domain boundaries, no ADR updates required (follows existing property pattern)
- **Contract-First Experience APIs**: Preserves public API contract for DirectorAgent.event_bus access, ensuring backward compatibility
- **Data Stewardship & Persistence Discipline**: No data persistence changes, only test expectation updates
- **Quality Engineering & Testing Discipline**: Fixes 5 failing tests (4 DirectorAgent, 1 data model), restores test suite to passing state, maintains test coverage
- **Operability, Security & Reliability**: No operational impact, improves code reliability by fixing test failures
- **Documentation & Knowledge Stewardship**: No documentation updates required (internal fix following existing patterns)
- Workbook Reference: N/A - Internal test fixes following established patterns

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 5 identified test failures pass after fixes are applied
- **SC-002**: DirectorAgent API maintains 100% backward compatibility for event_bus access across all 9 usage locations
- **SC-003**: Test suite completes without syntax errors or collection failures
- **SC-004**: Zero regression in passing tests - all previously passing tests continue to pass
- **SC-005**: Code changes follow existing architectural patterns (property delegation) without introducing new patterns

## Assumptions *(if any)*

- DirectorAgent refactoring to composition pattern was intentional and should be preserved
- Data model validation refactoring from "blessed" to "enhanced" terminology was intentional
- External code depending on `director.event_bus` API should continue to work without modification
- Property delegation pattern is the preferred approach for maintaining backward compatibility (follows existing code patterns)
- Test expectations should match current implementation, not preserve obsolete naming conventions

## Dependencies & Constraints *(if any)*

### Dependencies

- DirectorAgent composition architecture (DirectorAgentBase, TurnOrchestrator, WorldStateCoordinator)
- EventBus implementation and subscription mechanism
- Data model validation infrastructure (StandardResponse, validate_enhanced_data_model)
- Existing test infrastructure (unittest, pytest)

### Constraints

- Must not break existing property access patterns (registered_agents, current_turn_number, simulation_start_time, etc.)
- Must not modify internal composition structure (self.base.event_bus)
- Must maintain backward compatibility for legacy function alias (validate_blessed_data_model)
- Must follow existing code style and architectural patterns
- Cannot introduce breaking changes to public APIs

## Out of Scope *(if any)*

- Refactoring additional DirectorAgent methods or properties
- Changing data model validation logic or behavior
- Updating other validation string values throughout the codebase
- Fixing integration tests that require running services
- Addressing deprecation warnings or other non-blocking test issues
- Optimizing test performance or reducing test execution time
- Adding new test coverage beyond fixing existing failures
