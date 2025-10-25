# Phase 4: Complete Test Failure Fix Plan

## Executive Summary
- **Current Status**: 1878/2248 tests passing (83.5%)
- **Failures**: 266 failed + 52 errors = 318 total issues
- **Target**: 100% passing (2248/2248)
- **Estimated Effort**: 8-12 hours
- **Risk Level**: Medium (many legacy test files involved)

---

## Priority Matrix

### 🔴 CRITICAL (Must Fix First) - 78 failures
1. **event_bus Parameter** (52 errors) - Blocks test execution
2. **ContextLoaderService** (20 failures) - Core functionality
3. **BridgeConfiguration** (6 errors) - Import missing

### 🟡 HIGH (Should Fix) - 64 failures  
4. **Value Object Equality** (40 failures) - Design pattern issue
5. **ChroniclerAgent Story** (24 failures) - Duplicate of #1

### 🟢 MEDIUM (Nice to Have) - 176 failures
6. **DirectorAgent Refactored** (15 failures) - Interface changes
7. **Interaction Proposals** (3 failures) - Time mocking needed
8. **InteractionId Validation** (2 failures) - Input validation
9. **WorldStateAggregate** (1 failure) - Single test
10. **Missing SQLAlchemy** (1 failure) - Optional dependency

---

## Detailed Execution Plan

### Phase 4.1: Analysis & Categorization (30 mins)
**Status**: ✅ COMPLETED

**Deliverables**:
- [x] Complete failure analysis documented
- [x] Categories identified (10 categories)
- [x] Priority matrix created
- [x] Fix strategies outlined

---

### Phase 4.2: Fix event_bus Parameter (52 errors) - 2 hours
**Priority**: 🔴 CRITICAL
**Impact**: Fixes 52 errors immediately
**Risk**: LOW - straightforward parameter addition

#### Files to Fix:
1. `tests/unit/test_unit_director_agent.py` (6 tests)
2. `tests/unit/test_unit_chronicler_agent.py` (11 tests)  
3. `tests/unit/test_director_agent_comprehensive.py` (5 tests)
4. `tests/unit/test_director_agent_advanced.py` (4 tests)
5. `tests/test_iron_laws.py` (26 tests)
6. `tests/test_integration_complete.py` (1 test)

#### Implementation Steps:
1. Create reusable fixture in `tests/conftest.py`:
   ```python
   @pytest.fixture
   def mock_event_bus():
       return Mock(spec=['subscribe', 'publish', 'unsubscribe'])
   ```

2. Update DirectorAgent instantiation pattern:
   ```python
   # BEFORE:
   director = DirectorAgent()
   
   # AFTER:
   director = DirectorAgent(event_bus=mock_event_bus)
   ```

3. Update ChroniclerAgent instantiation:
   ```python
   # BEFORE:
   chronicler = ChroniclerAgent()
   
   # AFTER:
   chronicler = ChroniclerAgent(event_bus=mock_event_bus)
   ```

4. Batch process all affected test files using Task tool
5. Validate with act CLI after each file

**Success Criteria**:
- All 52 errors resolved
- act CLI shows 0 errors for event_bus
- No new failures introduced

---

### Phase 4.3: Fix BridgeConfiguration (6 errors) - 30 mins
**Priority**: 🔴 CRITICAL  
**Impact**: Fixes 6 errors
**Risk**: MEDIUM - need to locate/restore class

#### Investigation Steps:
1. Search for BridgeConfiguration in codebase:
   ```bash
   grep -r "class BridgeConfiguration" src/
   ```

2. Check git history for removal:
   ```bash
   git log --all --full-history -- "*BridgeConfiguration*"
   ```

#### Fix Options:
**Option A**: Class still exists - add import
- Add `from src.xxx import BridgeConfiguration` to test file
  
**Option B**: Class removed - create mock
```python
@pytest.fixture
def mock_bridge_config():
    config = Mock()
    config.max_agents = 10
    config.timeout = 30
    return config
```

**Option C**: Class renamed - update references
- Find new name and update all test references

**Success Criteria**:
- All 6 BridgeConfiguration errors resolved
- Tests using proper import or mock

---

### Phase 4.4: Fix ContextLoaderService (20 failures) - 1.5 hours
**Priority**: 🔴 CRITICAL
**Impact**: Fixes 20 failures
**Risk**: MEDIUM - may require source code changes

#### Root Cause Analysis:
Error: `'dict' object has no attribute 'name'`

This suggests ContextLoaderService expects an object but receives dict.

#### Investigation:
1. Read `src/contexts/character/application/services/context_loader.py`
2. Read `tests/unit/contexts/character/application/services/test_context_loader.py`
3. Identify where dict is passed instead of object

#### Fix Strategy (Choose One):
**Strategy A**: Fix the service to handle dict
```python
# In ContextLoaderService
def load_context(self, data):
    if isinstance(data, dict):
        # Convert dict to proper object
        return ContextObject(**data)
    return data
```

**Strategy B**: Fix tests to pass proper objects
```python
# In tests
context_data = CharacterContext(name="Test", age=25, ...)  # Object
# Instead of:
context_data = {"name": "Test", "age": 25}  # Dict
```

**Strategy C**: Use dataclass/pydantic for automatic conversion

**Success Criteria**:
- All 20 ContextLoaderService tests pass
- No 'dict has no attribute' errors
- Consistent data handling pattern

---

### Phase 4.5: Fix Value Object Equality (40 failures) - 2 hours
**Priority**: 🟡 HIGH
**Impact**: Fixes 40 failures
**Risk**: MEDIUM - affects domain design

#### Affected Value Objects:
1. CausalNode
2. NarrativeContext  
3. NarrativeTheme
4. PlotPoint
5. StoryPacing

#### Root Cause:
```python
# creation_timestamp differs by microseconds
timestamp1: datetime(2025, 10, 25, 4, 23, 42, 193809)
timestamp2: datetime(2025, 10, 25, 4, 23, 42, 193850)
# Result: object1 != object2 even with same data
```

#### Fix Strategy (Recommended):
**Option A**: Exclude timestamp from equality (RECOMMENDED)
```python
def __eq__(self, other):
    if not isinstance(other, self.__class__):
        return False
    # Compare all fields EXCEPT creation_timestamp
    return (self.id == other.id and 
            self.type == other.type and
            self.title == other.title and
            # ... other fields
            # NOT: self.creation_timestamp == other.creation_timestamp
            )

def __hash__(self):
    # Hash only stable fields, exclude timestamp
    return hash((self.id, self.type, self.title, ...))
```

**Option B**: Use freezegun to freeze time in tests
```python
from freezegun import freeze_time

@freeze_time("2025-10-25 12:00:00")
def test_equality():
    node1 = CausalNode(...)
    node2 = CausalNode(...)
    assert node1 == node2  # timestamps will be identical
```

**Recommendation**: Use Option A for production code quality

#### Implementation:
1. Update `__eq__` and `__hash__` in each value object
2. Ensure business identity (id, type, name) determines equality
3. Keep creation_timestamp for audit but exclude from comparison

**Success Criteria**:
- All 40 value object equality tests pass
- Value objects usable in sets and as dict keys
- Consistent equality semantics across all VOs

---

### Phase 4.6: Fix ChroniclerAgent Story Generation (24 failures) - 30 mins
**Priority**: 🟡 HIGH
**Impact**: Fixes 24 failures  
**Risk**: LOW - duplicate of Phase 4.2

#### Files:
- `tests/test_story_generation_comprehensive.py`

#### Implementation:
Same fix as Phase 4.2 - add event_bus parameter to all ChroniclerAgent instantiations.

**Pattern**:
```python
# Update all fixtures in the file
@pytest.fixture
def chronicler(mock_event_bus):
    return ChroniclerAgent(event_bus=mock_event_bus)
```

**Success Criteria**:
- All 24 story generation tests pass
- ChroniclerAgent properly initialized with event_bus

---

### Phase 4.7: Fix DirectorAgent Refactored (15 failures) - 2 hours
**Priority**: 🟢 MEDIUM
**Impact**: Fixes 15 failures
**Risk**: MEDIUM - interface breaking changes

#### Root Causes:
1. Missing `initialize` method on managers
2. Missing properties: `agents`, `event_bus`, `generate_narrative_context`
3. Changed status structure (no `is_initialized` key)

#### Investigation:
1. Read current DirectorAgent implementation
2. Compare with test expectations
3. Identify deprecated vs. new interface

#### Fix Approaches:
**Approach A**: Update DirectorAgent to restore compatibility
- Add deprecated methods with warnings
- Maintain backward compatibility layer

**Approach B**: Update tests to match new interface (RECOMMENDED)
- Remove calls to deprecated methods
- Use new property names and structure
- Update assertions to match new status format

**Approach C**: Mark tests as legacy and skip
- Add `@pytest.mark.skip(reason="Legacy interface, to be refactored")`

**Recommendation**: Use Approach B for clean codebase

#### Implementation:
1. Map old interface → new interface
2. Update test assertions
3. Remove deprecated method calls
4. Use new property access patterns

**Success Criteria**:
- All 15 DirectorAgent refactored tests pass
- Tests use current DirectorAgent interface
- No deprecated method calls

---

### Phase 4.8: Fix Interaction Proposals (3 failures) - 30 mins
**Priority**: 🟢 MEDIUM
**Impact**: Fixes 3 failures
**Risk**: LOW - time mocking

#### Root Cause:
Proposals expire before test can submit them.

#### Fix:
```python
from freezegun import freeze_time
from unittest.mock import patch

@freeze_time("2025-10-25 12:00:00")
def test_submit_proposal_success():
    # Proposal created at frozen time
    proposal = create_proposal()
    
    # Still frozen time when submitting
    result = service.submit_proposal(proposal)
    
    assert result.success
```

**Alternative**: Extend expiration period
```python
proposal = create_proposal(expires_in=timedelta(hours=24))
```

**Success Criteria**:
- All 3 proposal tests pass
- Proposals don't expire during test execution

---

### Phase 4.9: Fix InteractionId Validation (2 failures) - 20 mins  
**Priority**: 🟢 MEDIUM
**Impact**: Fixes 2 failures
**Risk**: LOW - simple validation

#### Root Cause:
`InteractionId.from_string()` not raising ValueError for invalid formats.

#### Fix:
```python
@classmethod
def from_string(cls, value: str) -> "InteractionId":
    if not isinstance(value, str):
        raise ValueError(f"Expected string, got {type(value)}")
    
    if not value or "_" not in value:
        raise ValueError(f"Invalid InteractionId format: {value}")
    
    # Parse and validate format
    parts = value.split("_")
    if len(parts) != expected_parts:
        raise ValueError(f"Invalid format: {value}")
    
    return cls(value)
```

**Success Criteria**:
- Invalid formats raise ValueError
- Non-string types raise ValueError
- Valid formats parse correctly

---

### Phase 4.10: Fix WorldStateAggregate (1 failure) - 15 mins
**Priority**: 🟢 LOW
**Impact**: Fixes 1 failure
**Risk**: LOW - single test

#### Steps:
1. Read exact error from act CLI output
2. Read test file
3. Fix specific issue
4. Validate

---

### Phase 4.11: Fix Missing SQLAlchemy (1 error) - 10 mins
**Priority**: 🟢 LOW  
**Impact**: Fixes 1 error
**Risk**: LOW - dependency management

#### Options:
**Option A**: Add to requirements.txt (if needed)
```txt
sqlalchemy>=2.0.0
```

**Option B**: Make import optional
```python
try:
    from sqlalchemy import ...
except ImportError:
    # Fallback or skip tests
    pytest.skip("sqlalchemy not installed")
```

**Recommendation**: Check if sqlalchemy is actually needed. If not, remove the import.

---

### Phase 4.12: Final Validation - 1 hour
**Priority**: 🔴 CRITICAL
**Impact**: Confirms all fixes work
**Risk**: LOW

#### Steps:
1. Run act CLI with all Python versions (3.9, 3.10, 3.11, 3.12)
2. Verify 0 errors, 0 failures
3. Check coverage hasn't decreased
4. Review any new warnings

**Success Criteria**:
```
= 2248 passed, 0 failed, 0 errors in XXX.XXs =
```

---

## Timeline & Resource Allocation

### Day 1 (4 hours)
- ✅ Phase 4.1: Analysis (30 min) - DONE
- Phase 4.2: event_bus fixes (2 hours)
- Phase 4.3: BridgeConfiguration (30 min)
- Phase 4.4: ContextLoaderService start (1 hour)

### Day 2 (4 hours)
- Phase 4.4: ContextLoaderService complete (30 min)
- Phase 4.5: Value Object Equality (2 hours)
- Phase 4.6: ChroniclerAgent Story (30 min)
- Phase 4.7: DirectorAgent Refactored start (1 hour)

### Day 3 (4 hours)
- Phase 4.7: DirectorAgent Refactored complete (1 hour)
- Phase 4.8-4.11: Minor fixes (1.5 hours)
- Phase 4.12: Final validation (1 hour)
- Buffer time (30 min)

**Total Estimated Time**: 12 hours
**Critical Path**: Phase 4.2 → 4.3 → 4.4 → 4.12
**Parallelizable**: Phases 4.5-4.11 can be done in any order after Phase 4.2

---

## Risk Mitigation

### High-Risk Areas:
1. **ContextLoaderService** - May require source code refactoring
2. **DirectorAgent Refactored** - Interface breaking changes
3. **Value Object Equality** - Affects domain model design

### Mitigation Strategies:
1. **Create feature branch** for Phase 4 work
2. **Commit after each phase** for easy rollback
3. **Use act CLI validation** after each major change
4. **Keep backup** of working tests before modification

---

## Success Metrics

### Quantitative:
- ✅ 0 errors (currently 52)
- ✅ 0 failures (currently 266)  
- ✅ 2248/2248 tests passing (currently 1878/2248)
- ✅ Coverage ≥80% (maintained or improved)

### Qualitative:
- ✅ Clean act CLI output
- ✅ No deprecated warnings
- ✅ Consistent test patterns
- ✅ Well-documented fixes

---

## Next Actions

### Immediate (Start Phase 4.2):
```bash
# 1. Create feature branch
git checkout -b phase4-fix-tests

# 2. Add event_bus fixture to conftest.py
# 3. Fix tests/unit/test_unit_director_agent.py
# 4. Validate with act CLI
# 5. Commit and continue
```

### Tools Needed:
- ✅ act CLI (already configured)
- ✅ Task tool (for parallel file processing)
- ✅ grep/ripgrep (for pattern search)
- ⬜ freezegun (for time mocking) - `pip install freezegun`

---

**Ready to proceed with Phase 4.2?**
