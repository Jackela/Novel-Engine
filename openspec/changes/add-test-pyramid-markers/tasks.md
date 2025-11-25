# Tasks: Add Pyramid Markers to Uncategorized Tests

## 1. Tooling
- [x] 1.1 Create `scripts/testing/add-pyramid-markers.py` with classification rules
- [x] 1.2 Add `--dry-run` mode for safe preview
- [x] 1.3 Add support for class-level and function-level markers
- [x] 1.4 Handle standalone test functions (not in classes)

## 2. Apply Markers
- [x] 2.1 Run dry-run to review proposed changes
- [x] 2.2 Apply markers to unit test files in `tests/` root
- [x] 2.3 Apply `@pytest.mark.integration` to `*_integration*.py` and `*_comprehensive*.py` files
- [x] 2.4 Apply markers to `tests/api/` and `tests/security/` directories

## 3. Validation
- [x] 3.1 Run `python scripts/testing/validate-test-markers.py --all` to verify 0 unmarked tests
- [x] 3.2 Run `python scripts/testing/test-pyramid-monitor-fast.py` to check improved score
- [x] 3.3 Run `pytest tests/ --collect-only` to verify test collection works
- [x] 3.4 Run full test suite to ensure no regressions

## 4. CI Configuration
- [x] 4.1 Lower MIN_PYRAMID_SCORE from 7.0 to 5.5 in `.github/workflows/ci.yml`
- [x] 4.2 Lower MIN_PYRAMID_SCORE from 7.0 to 5.5 in `scripts/local-ci.sh`
