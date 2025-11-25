# Test Speed Classification - Usage Examples

## Quick Start Examples

### Example 1: Developer Making Changes

**Scenario**: You're working on a character module and want quick feedback.

```bash
# Step 1: Make your code changes
vim src/contexts/character/domain/character_aggregate.py

# Step 2: Run only fast character tests (< 2 seconds)
pytest -m "character and fast" tests/unit/contexts/character/ -v

# Step 3: If fast tests pass, run all character tests
pytest tests/unit/contexts/character/ -v
```

### Example 2: Pre-commit Validation

**Scenario**: Before committing, run a quick sanity check.

```bash
# Run all fast tests (< 30 seconds)
./scripts/testing/run-fast-tests.sh

# Or just fast unit tests
pytest -m "unit and fast" tests/unit/ -q --tb=short
```

### Example 3: CI Pipeline Setup

**Scenario**: Set up a multi-stage CI pipeline.

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  fast-tests:
    name: Fast Tests (< 100ms)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -e .[test]
      - name: Run fast tests
        run: pytest -m "fast" tests/ -v --no-cov

  standard-tests:
    name: Standard Tests (exclude slow)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -e .[test]
      - name: Run standard tests
        run: pytest -m "not slow" tests/ -v --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  slow-tests:
    name: Slow Tests (nightly)
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -e .[test]
      - name: Run slow tests
        run: pytest -m "slow" tests/ -v
```

### Example 4: Analyzing Test Performance

**Scenario**: Identify slow tests that need optimization.

```bash
# Step 1: Generate comprehensive speed report
python scripts/testing/test-speed-report.py tests/unit/ > unit_speed_report.txt

# Step 2: Review the slowest tests
grep -A 20 "Top 10 Slowest" unit_speed_report.txt

# Step 3: Focus on optimizing slow tests
# Output shows:
#   1.620s  tests/unit/.../test_cache_expiration
#   1.110s  tests/unit/.../test_concurrent_load_limit
#   0.540s  tests/unit/.../test_caching_functionality
```

### Example 5: Adding Markers to New Tests

**Scenario**: You've written new tests and want to mark them.

```bash
# Method 1: Automatic (recommended)
python scripts/testing/add-speed-markers.py --test-path tests/unit/my_new_tests/

# Method 2: Manual
# Add markers based on expected performance:
@pytest.mark.unit
@pytest.mark.fast
def test_simple_validation():
    """Fast test: simple data validation."""
    assert validate_data("test") == True

@pytest.mark.unit
@pytest.mark.medium
def test_database_query():
    """Medium test: involves database I/O."""
    result = db.query("SELECT * FROM users")
    assert len(result) > 0

@pytest.mark.unit
@pytest.mark.slow
def test_full_integration():
    """Slow test: complete workflow with sleeps."""
    await asyncio.sleep(1.5)
    result = process_complete_workflow()
    assert result.success
```

### Example 6: Watch Mode Development

**Scenario**: Continuous testing during development.

```bash
# Install pytest-watch
pip install pytest-watch

# Watch only fast tests for instant feedback
ptw -m "fast" tests/unit/contexts/character/ -- -v --tb=short

# Or use entr for file watching
ls tests/unit/**/*.py | entr -c pytest -m "fast" tests/unit/ -q
```

### Example 7: Selective Test Runs

**Scenario**: Run specific combinations of tests.

```bash
# Fast unit tests only
pytest -m "unit and fast" tests/unit/

# Fast or medium integration tests
pytest -m "integration and (fast or medium)" tests/integration/

# All knowledge tests except slow ones
pytest -m "knowledge and not slow" tests/

# Character tests that are fast
pytest -m "character and fast" tests/ -v

# Narrative tests that aren't slow
pytest -m "narrative and not slow" tests/
```

### Example 8: Performance Benchmarking

**Scenario**: Track test suite performance over time.

```bash
# Generate baseline report
python scripts/testing/test-speed-report.py tests/ > baseline_report.txt

# After optimization, generate new report
python scripts/testing/test-speed-report.py tests/ > optimized_report.txt

# Compare
diff baseline_report.txt optimized_report.txt
```

### Example 9: Debugging Slow Tests

**Scenario**: A test is slower than expected.

```bash
# Step 1: Identify the slow test
pytest tests/unit/contexts/character/test_slow.py::test_function -v --durations=0

# Output shows:
# 2.340s call     test_function
# 0.500s setup    test_function
# 0.020s teardown test_function

# Step 2: Profile the test
pytest tests/unit/contexts/character/test_slow.py::test_function --profile

# Step 3: Add appropriate marker
# If > 1s, add @pytest.mark.slow
# If 100ms-1s, add @pytest.mark.medium
```

### Example 10: Team Workflow

**Scenario**: Establish team standards.

```bash
# .git/hooks/pre-commit
#!/bin/bash
# Run fast tests before allowing commit
pytest -m "fast" tests/ -q --tb=short
if [ $? -ne 0 ]; then
    echo "Fast tests failed! Fix before committing."
    exit 1
fi

# Makefile
.PHONY: test-fast test-standard test-all

test-fast:
	@echo "Running fast tests..."
	pytest -m "fast" tests/ -q --tb=short --no-cov

test-standard:
	@echo "Running standard tests (excluding slow)..."
	pytest -m "not slow" tests/ -v --cov=src

test-all:
	@echo "Running all tests including slow ones..."
	pytest tests/ -v --cov=src

test-slow-only:
	@echo "Running only slow tests..."
	pytest -m "slow" tests/ -v
```

## Common Patterns

### Pattern 1: Progressive Testing
```bash
# Level 1: Fast (during development)
pytest -m "fast" tests/ -q

# Level 2: Standard (before PR)
pytest -m "not slow" tests/ -v

# Level 3: Complete (before merge)
pytest tests/ -v
```

### Pattern 2: Component-Specific Speed Testing
```bash
# Fast character tests
pytest -m "character and fast" tests/

# Medium narrative tests
pytest -m "narrative and medium" tests/

# All AI tests except slow
pytest -m "ai and not slow" tests/
```

### Pattern 3: Time-Based Selection
```bash
# Under 30 seconds (fast only)
pytest -m "fast" tests/

# Under 2 minutes (fast + medium)
pytest -m "fast or medium" tests/

# Complete suite (all)
pytest tests/
```

## Tips and Best Practices

### Tip 1: Consistent Marking
Always mark new tests based on actual performance:
- Measure first: `pytest --durations=10`
- Then mark appropriately

### Tip 2: Optimize Slow Tests
If a test is marked slow:
1. Can setup/teardown be optimized?
2. Can fixtures be cached?
3. Can sleeps be reduced/mocked?
4. Should it be an integration test instead?

### Tip 3: CI Optimization
```yaml
# Don't run slow tests on every PR
- if: github.event_name == 'pull_request'
  run: pytest -m "not slow" tests/

# Run all tests on main branch
- if: github.ref == 'refs/heads/main'
  run: pytest tests/
```

### Tip 4: Local Development
Add to shell aliases:
```bash
# ~/.bashrc or ~/.zshrc
alias pt='pytest'
alias ptf='pytest -m "fast" tests/ -q'
alias pts='pytest -m "not slow" tests/ -v'
alias pta='pytest tests/ -v'
```

## Troubleshooting

### Issue: Test is marked fast but takes > 100ms
```bash
# Verify actual timing
pytest path/to/test.py::test_name -v --durations=0

# If confirmed slow, update marker
# Change @pytest.mark.fast to @pytest.mark.medium or @pytest.mark.slow
```

### Issue: Marker not recognized
```bash
# Check pytest.ini has the marker defined
grep "markers" pytest.ini

# Verify pyproject.toml also has it
grep -A 5 "markers" pyproject.toml
```

### Issue: No tests collected
```bash
# Check marker spelling
pytest -m "fase" tests/  # Typo!
pytest -m "fast" tests/  # Correct

# List available markers
pytest --markers
```

## Summary

The test speed classification system provides:

✅ **10x faster feedback** during development
✅ **Flexible CI/CD** pipeline configuration
✅ **Data-driven optimization** of test suite
✅ **Clear team standards** for test performance

Use it to maintain a fast, efficient test suite while ensuring comprehensive coverage.
