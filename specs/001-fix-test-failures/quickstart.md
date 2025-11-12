# Quickstart: Fix Test Suite Failures

**Feature**: Fix Test Suite Failures  
**Branch**: `001-fix-test-failures`  
**Date**: 2025-11-03

## Overview

This quickstart guides developers through applying the test suite fixes for DirectorAgent API compatibility and data model validation test updates.

## Prerequisites

- Python 3.12.6+ installed
- Repository cloned and on branch `001-fix-test-failures`
- Development environment set up (pytest 8.4.2)

## Quick Start (5 minutes)

### Step 1: Apply Fixes

**Fix 1: Add event_bus property to DirectorAgent**

File: `director_agent_integrated.py` (line ~446, after `world_state_data` property)

```python
@property
def event_bus(self) -> EventBus:
    """Get event bus instance."""
    return self.base.event_bus
```

**Fix 2: Update data model validation test assertion**

File: `tests/test_data_models.py` (line 493)

```python
# Change from:
assert result.data["validation"] == "blessed_by_PRIME ARCHITECT"

# To:
assert result.data["validation"] == "verified_by_prime_architect"
```

### Step 2: Validate Fixes

Run the affected tests:

```bash
# Test DirectorAgent initialization (4 failures → 0)
python -m pytest tests/test_director_agent.py::TestDirectorAgent::test_initialization -v

# Test data model validation (1 failure → 0)
python -m pytest tests/test_data_models.py::TestSacredValidationFunctions::test_validate_blessed_data_model_success -v

# Run all affected tests
python -m pytest tests/test_director_agent.py tests/test_data_models.py::TestSacredValidationFunctions -v
```

**Expected Results**:
- ✅ 5 tests pass (previously failed)
- ✅ 0 failures
- ✅ 0 errors

### Step 3: Regression Check

Run the full unit test suite (excluding integration tests):

```bash
# Run unit tests only
python -m pytest tests/ -k "not (api or integration or e2e or requires_services)" -v --tb=short
```

**Expected Results**:
- ✅ 116+ tests pass (111 baseline + 5 fixed)
- ✅ 0 failures
- ✅ 0 regressions

## Detailed Steps

### Understanding the Fixes

**Problem 1: DirectorAgent Refactoring**

The DirectorAgent was refactored to use composition pattern:
- Before: `self.event_bus` (direct attribute)
- After: `self.base.event_bus` (composition)
- Impact: Broke public API across 9 usage locations

**Solution**: Add property delegation following existing pattern (8 other properties use same approach)

**Problem 2: Validation String Mismatch**

The validation function was renamed and string changed:
- Before: `validate_blessed_data_model` → `"blessed_by_PRIME ARCHITECT"`
- After: `validate_enhanced_data_model` → `"verified_by_prime_architect"`
- Impact: 1 test still expects old string

**Solution**: Update test assertion to match current implementation

### Manual Verification

**Verify property delegation works**:
```python
from director_agent import DirectorAgent
from unittest.mock import Mock
from src.event_bus import EventBus

mock_bus = Mock(spec=EventBus)
director = DirectorAgent(event_bus=mock_bus)

# Verify property returns exact instance
assert director.event_bus is mock_bus
print("✅ Property delegation works")
```

**Verify validation string**:
```python
from src.core.data_models import validate_blessed_data_model, MemoryItem

memory = MemoryItem(agent_id="test", content="Test")
result = validate_blessed_data_model(memory)

# Verify current string value
assert result.data["validation"] == "verified_by_prime_architect"
print("✅ Validation string correct")
```

## Testing Strategy

### Test Coverage

**Primary Tests (5 failures fixed)**:
1. `tests/test_director_agent.py::TestDirectorAgent::test_initialization`
2. `tests/test_director_agent.py::TestDirectorAgent::test_handle_agent_action`
3. `tests/test_director_agent.py::TestDirectorAgent::test_handle_agent_action_with_no_action`
4. `tests/test_director_agent.py::TestDirectorAgent::test_run_turn_emits_event`
5. `tests/test_data_models.py::TestSacredValidationFunctions::test_validate_blessed_data_model_success`

**Secondary Validation (9 usage locations)**:
- `tests/unit/agents/test_director_refactored.py:361`
- `tests/unit/test_director_agent_comprehensive.py:68,85,106,130,142`
- `tests/unit/test_unit_director_agent.py:52,275`

**Regression Tests**:
- All 111 passing unit tests must continue to pass
- No new failures introduced
- Test execution time remains consistent

### Continuous Integration

**CI Pipeline Validation**:
```bash
# Full test suite (CI environment)
python -m pytest --verbose --tb=short --maxfail=1

# With coverage
python -m pytest --cov=src --cov=director_agent_integrated --cov-report=term-missing
```

**Expected CI Results**:
- ✅ Test suite passes
- ✅ No syntax errors or collection failures
- ✅ Coverage maintained or improved

## Troubleshooting

### Issue: Property not found

**Symptom**: `AttributeError: 'DirectorAgent' object has no attribute 'event_bus'`

**Solution**: 
- Verify property was added to `director_agent_integrated.py`
- Check indentation (property must be at class level)
- Confirm file was saved

### Issue: Test still fails with validation string

**Symptom**: `AssertionError: assert 'verified_by_prime_architect' == 'blessed_by_PRIME ARCHITECT'`

**Solution**:
- Verify test assertion was updated in `tests/test_data_models.py:493`
- Confirm exact string match: `"verified_by_prime_architect"`
- Check for typos (underscore vs space, capitalization)

### Issue: New test failures

**Symptom**: Tests that previously passed now fail

**Solution**:
- Revert changes and verify baseline state
- Run tests individually to isolate issue
- Check for unintended modifications to other files

## Next Steps

After completing the quickstart:

1. **Commit changes**: Create commit with both fixes
2. **Run full test suite**: Validate zero regression
3. **Update checklist**: Mark implementation complete
4. **Create PR**: Submit for code review

## Success Criteria

- [x] 5 failing tests now pass
- [x] 111 passing tests remain passing (zero regression)
- [x] Property delegation follows existing patterns
- [x] Test assertions match current implementation
- [x] No new test failures introduced

## Resources

- **Specification**: [spec.md](./spec.md)
- **Implementation Plan**: [plan.md](./plan.md)
- **Technical Research**: [research.md](./research.md)
- **Data Model**: [data-model.md](./data-model.md)
