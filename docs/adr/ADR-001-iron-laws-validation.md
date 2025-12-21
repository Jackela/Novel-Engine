# ADR-001: Iron Laws Validation System

**Status**: Accepted  
**Date**: 2025-08-11  
**Deciders**: Architecture Team  

## Context

The Novel Engine requires a robust system to validate AI agent actions to prevent illogical, inconsistent, or world-breaking behaviors. Without validation, agents could:

- Create impossible scenarios (negative resources, teleportation)
- Act on information they shouldn't have (omniscience)
- Violate established world rules or character capabilities
- Break canonical constraints from source material

Multiple validation approaches were considered for the multi-agent narrative simulation system.

## Decision

We will implement an "Iron Laws" validation system with 5 fundamental rules enforced by an Adjudicator component:

1. **Resource Conservation**: Actions cannot result in negative resource values
2. **Information Limit**: Actions can only target entities visible to the actor  
3. **State Consistency**: Actions must be permitted for current entity state
4. **Rule Adherence**: Actions cannot contradict established world rules
5. **Canon Preservation**: Actions cannot violate canonical source material constraints

### Implementation Details

- **Adjudicator Component**: Validates every action before execution
- **Specific Error Codes**: E001-E005 corresponding to each law violation
- **Repair Mechanism**: Automatic action modification when possible
- **Fail-Fast**: Invalid actions rejected immediately with detailed feedback

## Alternatives Considered

### 1. **LLM-Based Validation**
Use the LLM to evaluate action validity through prompting.

**Pros**:
- Natural language understanding of complex scenarios
- Flexible adaptation to edge cases
- No need to enumerate all rules explicitly

**Cons**:
- Non-deterministic results (same action might validate differently)
- High latency (additional LLM calls for every action)
- Difficult to debug validation failures
- Token cost scales with validation complexity
- Unreliable for critical system integrity

### 2. **Physics Engine Integration**
Integrate a physics engine to validate spatial and physical constraints.

**Pros**:
- Realistic physical validation
- Well-established collision detection and movement validation
- Deterministic results

**Cons**:
- Overkill for narrative simulation needs
- High computational overhead
- Complex integration with abstract game mechanics
- Limited to physical constraints only

### 3. **Rule-Based Expert System**
Implement a comprehensive rule-based system with hundreds of specific rules.

**Pros**:
- Extremely detailed validation possible
- Deterministic and debuggable
- Can encode domain expertise precisely

**Cons**:
- Exponential complexity as rules interact
- Difficult to maintain and extend
- Rule conflicts require sophisticated resolution
- Performance degrades with rule count

### 4. **Statistical Validation Model**
Train a machine learning model on valid vs. invalid action examples.

**Pros**:
- Learns complex patterns automatically
- Good performance once trained
- Adaptable to new scenarios

**Cons**:
- Requires large training dataset
- Black box decision making
- Non-deterministic edge case behavior
- Difficult to explain validation failures
- Training overhead and model updates

## Consequences

### Positive

1. **Deterministic Validation**: Same action always produces same validation result
2. **Fast Performance**: Rule-based validation is sub-millisecond
3. **Clear Error Messages**: Specific error codes make debugging straightforward
4. **Maintainable**: Only 5 laws to understand and maintain
5. **Extensible**: New constraints can be added to existing laws
6. **Debuggable**: Developers can trace exactly why actions fail
7. **Automatic Repair**: Invalid actions can often be automatically corrected
8. **System Integrity**: Prevents impossible world states

### Negative

1. **Rigidity**: May reject creative actions that should be allowed
2. **Implementation Complexity**: Each law requires careful implementation
3. **Edge Cases**: Complex scenarios may not fit neatly into the 5 laws
4. **Maintenance Overhead**: Laws must be updated as game mechanics evolve
5. **Conservative Bias**: System errs on side of rejection rather than acceptance

### Risks and Mitigation

**Risk**: Over-restrictive validation reduces narrative creativity  
**Mitigation**: Repair mechanisms attempt to modify rather than reject actions

**Risk**: Complex edge cases break validation logic  
**Mitigation**: Comprehensive test coverage for edge cases, with fallback to human review

**Risk**: Performance degradation with complex world states  
**Mitigation**: Optimize validation order, cache frequently-checked conditions

## Implementation Notes

### Error Code Design
- **E001_RESOURCE_NEGATIVE**: Resource conservation violations
- **E002_TARGET_INVALID**: Information limit violations  
- **E003_ACTION_IMPOSSIBLE**: State consistency violations
- **E004_LOGIC_VIOLATION**: Rule adherence violations
- **E005_CANON_BREACH**: Canon preservation violations

### Validation Order
Laws are checked in order of performance impact (fastest first):
1. Resource Conservation (simple arithmetic)
2. State Consistency (entity state lookup)
3. Information Limit (visibility calculation)
4. Rule Adherence (rule evaluation)
5. Canon Preservation (content analysis)

### Integration Points
- **Director Agent**: Calls adjudication before applying effects
- **API Layer**: Returns HTTP 409 with error details for invalid actions
- **Replay System**: Logs validation decisions for analysis
- **Testing**: Each law has dedicated test coverage

## Related Decisions
- ADR-002: Fog of War system provides input to Information Limit validation
- ADR-004: Context Supply Chain feeds world state to validation system

## Status Changes
- 2025-08-11: Proposed and accepted during initial architecture design