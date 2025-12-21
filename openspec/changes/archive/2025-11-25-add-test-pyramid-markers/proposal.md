# Change: Add Pyramid Markers to Uncategorized Tests

## Why
CI quality gates are failing because 498 tests lack pyramid markers (`@pytest.mark.unit`, `@pytest.mark.integration`, or `@pytest.mark.e2e`). The current test pyramid score is 1.76/10 against a threshold of 7.0. The missing markers penalty alone accounts for ~4.76 points of the deficit.

## What Changes
- Create `scripts/testing/add-pyramid-markers.py` to bulk-add pyramid markers based on file location and naming conventions
- Apply `@pytest.mark.unit` to tests in `tests/` root directory (default)
- Apply `@pytest.mark.integration` to tests with `_integration` or `_comprehensive` in filename, or in `tests/api/`
- Ensure all ~498 uncategorized tests receive appropriate pyramid markers

## Impact
- Affected specs: `ci-parity` (related), new `test-pyramid-compliance` capability
- Affected code:
  - `scripts/testing/add-pyramid-markers.py` (new)
  - `tests/*.py` (~27 files in root)
  - `tests/api/*.py` (~2 files)
  - `tests/security/*.py` (~2 files)
- CI quality gate: Pyramid score expected to improve from 1.76 to ~6.5+
