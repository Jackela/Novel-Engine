# CI Quality Gates Documentation

## Overview

The Novel Engine project implements comprehensive CI quality gates to ensure code quality, test coverage, and proper test classification. These gates automatically validate every commit and pull request.

## Quality Gates

### 1. Test Pyramid Score

**What it checks:** The distribution of tests across unit, integration, and E2E categories.

**Threshold:** 7.0/10.0 minimum score

**Target Distribution:**
- Unit tests: 70%
- Integration tests: 20%
- E2E tests: 10%

**Why it matters:** A healthy test pyramid ensures fast feedback, reliable tests, and sustainable test maintenance.

### 2. Test Marker Validation

**What it checks:** All test functions have proper pyramid markers.

**Required markers:** Every test must have one of:
- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Tests with external dependencies
- `@pytest.mark.e2e` - End-to-end workflow tests

**Why it matters:** Proper categorization enables selective test execution and pyramid monitoring.

### 3. Test Execution by Type

Tests are run in separate CI jobs by category:
- **Unit Tests**: Must pass (blocking)
- **Integration Tests**: Must pass (blocking)
- **E2E Tests**: Must pass (blocking)
- **Smoke Tests**: Critical path validation (blocking)

### 4. Speed Regression Detection

**What it checks:** Number of slow tests (>1000ms)

**Threshold:** Warning if >10 slow tests

**Why it matters:** Prevents test suite slowdown over time.

## Running Quality Gates Locally

### Quick Check (Recommended before commit)

```bash
# Run fast local CI checks
./scripts/local-ci.sh --fast
```

This runs:
- Test pyramid analysis
- Test marker validation
- Unit tests

**Time:** ~1-2 minutes

### Full Validation (Before push)

```bash
# Run complete CI validation locally
./scripts/local-ci.sh
```

This runs all checks including:
- Test pyramid analysis
- Test marker validation
- Unit, integration, and E2E tests
- Frontend tests
- Linting

**Time:** ~5-10 minutes

### Individual Checks

```bash
# Check pyramid score only
./scripts/local-ci.sh --pyramid

# Validate test markers only
./scripts/local-ci.sh --markers

# Run pyramid monitor with detailed report
python scripts/testing/test-pyramid-monitor-fast.py

# Validate specific test files
python scripts/testing/validate-test-markers.py tests/test_example.py

# Validate all tests
python scripts/testing/validate-test-markers.py --all --verbose
```

## Pre-commit Hooks

### Installation

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install
```

### What runs on commit

When you commit, pre-commit automatically:
1. Validates test markers in modified test files
2. Runs code formatting (black, isort)
3. Runs linting (flake8)
4. Checks for common issues (trailing whitespace, large files, etc.)

### Bypassing hooks

**Temporary bypass (use sparingly):**

```bash
# Skip all pre-commit hooks
git commit --no-verify -m "message"

# Skip specific hook
SKIP=validate-test-markers git commit -m "message"

# Include bypass keyword in commit message
git commit -m "WIP: temporary work [skip-marker-check]"
```

**When to bypass:**
- Work in progress commits on feature branches
- Generated code or migrations
- Emergency hotfixes (with team approval)

**Never bypass on:**
- Commits to main/develop
- Pull request merges
- Release commits

## CI Pipeline Flow

```
Push/PR
  |
  ├── Test Pyramid Check ────────┐
  |                               |
  ├── Validate Test Markers ──────┤
  |                               |
  ├── Unit Tests ─────────────────┤
  |                               |
  ├── Integration Tests ──────────┤── CI Success
  |                               |
  ├── E2E Tests ──────────────────┤
  |                               |
  ├── Smoke Tests ────────────────┤
  |                               |
  └── Speed Regression (warning)──┘
```

All jobs (except speed regression) must pass for CI to succeed.

## Understanding Failures

### Test Pyramid Failure

**Error:**
```
Test pyramid score (6.2) is below minimum threshold (7.0)
Please improve test distribution to match the pyramid (70% unit, 20% integration, 10% e2e)
```

**How to fix:**
1. Check the pyramid report in CI artifacts
2. Review the distribution:
   - Too many E2E tests? Convert some to integration or unit tests
   - Not enough unit tests? Add more isolated tests
3. Run locally: `python scripts/testing/test-pyramid-monitor-fast.py`
4. See recommendations in the report

### Missing Test Markers

**Error:**
```
✗ Test marker validation FAILED
Found 15 tests without pyramid markers
```

**How to fix:**
1. Run: `python scripts/testing/validate-test-markers.py --all --verbose`
2. Add appropriate markers to identified tests:
   ```python
   @pytest.mark.unit
   def test_example():
       assert True
   ```
3. Choose the right marker:
   - **unit**: No external dependencies, fast (<100ms ideal)
   - **integration**: Uses database, API, file system, etc.
   - **e2e**: Full workflow from start to finish

### Speed Regression Warning

**Warning:**
```
Found 25 slow tests (>1000ms). Consider optimization or reclassification.
```

**How to fix:**
1. Review slow tests: `python scripts/testing/test-speed-report.py`
2. Options:
   - Optimize the test (mock external calls, reduce data)
   - Reclassify to integration/e2e if appropriate
   - Mark as `@pytest.mark.slow` if necessarily slow

## Marker Guidelines

### Unit Tests (@pytest.mark.unit)

**Characteristics:**
- No external dependencies (database, API, file system)
- Fast execution (<100ms ideal)
- Test single units of code in isolation
- Use mocks/stubs for dependencies

**Example:**
```python
@pytest.mark.unit
def test_character_name_validation():
    """Test character name validation logic."""
    character = Character(name="Test Hero")
    assert character.name == "Test Hero"
    assert character.validate_name()
```

### Integration Tests (@pytest.mark.integration)

**Characteristics:**
- Tests interaction between components
- May use external dependencies (database, services)
- Slower than unit tests (100ms-1000ms)
- Tests real integrations, not mocked

**Example:**
```python
@pytest.mark.integration
async def test_character_persistence():
    """Test saving and loading character from database."""
    character = Character(name="Test Hero")
    await character.save()

    loaded = await Character.load(character.id)
    assert loaded.name == character.name
```

### E2E Tests (@pytest.mark.e2e)

**Characteristics:**
- Tests complete user workflows
- Uses full stack (database, API, services)
- Slowest tests (>1000ms)
- Tests critical business paths

**Example:**
```python
@pytest.mark.e2e
async def test_character_creation_workflow():
    """Test complete character creation and first quest."""
    # Create character
    response = await client.post("/characters", json={"name": "Hero"})
    character_id = response.json()["id"]

    # Start quest
    response = await client.post(f"/characters/{character_id}/quest")
    assert response.status_code == 200

    # Complete quest
    response = await client.put(f"/characters/{character_id}/quest/complete")
    assert response.json()["xp"] > 0
```

### Class-level Markers

Apply markers to all tests in a class:

```python
@pytest.mark.unit
class TestCharacterValidation:
    """All tests in this class are unit tests."""

    def test_name_validation(self):
        assert True

    def test_level_validation(self):
        assert True
```

## Additional Speed Markers

In addition to pyramid markers, add speed markers:

```python
@pytest.mark.unit
@pytest.mark.fast  # <100ms
def test_quick_operation():
    assert True

@pytest.mark.integration
@pytest.mark.medium  # 100ms-1000ms
def test_database_query():
    assert True

@pytest.mark.e2e
@pytest.mark.slow  # >1000ms
def test_full_workflow():
    assert True
```

## PR Comments

On pull requests, the CI will automatically comment with:
- Test pyramid score
- Distribution table
- Missing markers count
- Recommendations

Example:
```
✅ Test Pyramid Quality Gate - PASS

Score: 8.2/10.0 (Threshold: 7.0)

| Type | Count | Percentage | Target | Delta |
|------|-------|------------|--------|-------|
| Unit | 145 | 72.5% | 70% | +2.5% |
| Integration | 38 | 19.0% | 20% | -1.0% |
| E2E | 17 | 8.5% | 10% | -1.5% |

Total Tests: 200
```

## Monitoring Test Health

### View Historical Trends

```bash
# Check pyramid history
ls .pyramid-history/

# View latest report
cat .pyramid-history/latest.json
```

### Generate Reports

```bash
# Console report
python scripts/testing/test-pyramid-monitor-fast.py

# JSON report
python scripts/testing/test-pyramid-monitor-fast.py --format json

# HTML report
python scripts/testing/test-pyramid-monitor-fast.py --format html -o report.html

# Markdown report
python scripts/testing/test-pyramid-monitor-fast.py --format markdown
```

## Troubleshooting

### "No tests found with marker 'unit'"

**Cause:** Tests don't have pyramid markers.

**Fix:** Add markers to your tests or run validation:
```bash
python scripts/testing/validate-test-markers.py --all --verbose
```

### "Pyramid monitor failed to collect tests"

**Cause:** Tests directory structure issue.

**Fix:** Ensure tests are in `tests/` directory with `test_*.py` naming.

### "Score calculation seems wrong"

**Cause:** Tests might have multiple pyramid markers (only one should be used).

**Fix:** Each test should have exactly one pyramid marker (unit, integration, or e2e).

### Local CI fails but unsure why

**Debug:**
```bash
# Run with verbose output
./scripts/local-ci.sh --fast 2>&1 | tee ci-debug.log

# Check individual components
python scripts/testing/test-pyramid-monitor-fast.py --format console
python scripts/testing/validate-test-markers.py --all --verbose
pytest -m unit -v
```

## Best Practices

1. **Add markers when writing tests** - Don't wait until CI fails
2. **Run local CI before pushing** - Catch issues early
3. **Keep pyramid balanced** - Follow the 70/20/10 distribution
4. **Start with unit tests** - They're fastest and most valuable
5. **Reserve E2E for critical paths** - Don't overuse them
6. **Monitor speed** - Optimize or reclassify slow tests
7. **Review pyramid reports** - Learn from trends

## Getting Help

- Check this documentation
- Review example tests in `tests/` directory
- See `scripts/testing/README.md` for tool documentation
- Run tools with `--help` flag for usage
- Ask team members for guidance on test classification

## Configuration

### Adjusting Thresholds

Edit `.github/workflows/ci.yml`:
```yaml
env:
  MIN_PYRAMID_SCORE: '7.0'  # Adjust as needed
```

Edit `scripts/local-ci.sh`:
```bash
MIN_PYRAMID_SCORE=7.0  # Keep in sync with CI
```

### Customizing Targets

Edit `scripts/testing/test-pyramid-monitor-fast.py`:
```python
TARGETS = {
    "unit": 70.0,
    "integration": 20.0,
    "e2e": 10.0,
}
```

**Note:** Changing targets should be a team decision.

## Migration Guide

If you have existing tests without markers:

1. **Audit current tests:**
   ```bash
   python scripts/testing/validate-test-markers.py --all --verbose
   ```

2. **Classify tests systematically:**
   - Start with obvious unit tests
   - Identify integration tests (check for database/API usage)
   - Mark complex workflows as E2E

3. **Use batch adding script:**
   ```bash
   # Add unit marker to all tests in a file
   python scripts/testing/add-speed-markers.py tests/test_example.py --type unit
   ```

4. **Verify pyramid score:**
   ```bash
   python scripts/testing/test-pyramid-monitor-fast.py
   ```

5. **Iterate:** Adjust markers until score meets threshold

## Summary

Quality gates ensure:
- Healthy test pyramid distribution
- All tests properly categorized
- Fast CI feedback
- Sustainable test maintenance

**Key commands:**
- `./scripts/local-ci.sh --fast` - Quick pre-commit check
- `./scripts/local-ci.sh` - Full validation
- `python scripts/testing/validate-test-markers.py --all` - Check markers
- `python scripts/testing/test-pyramid-monitor-fast.py` - View pyramid

**Remember:** Quality gates exist to help maintain code quality. If you need to bypass them, always have a good reason and team approval.
