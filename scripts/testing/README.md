# Testing Tools - Quick Reference

## CI Quality Gates

### Local CI Validation
```bash
# Quick validation before commit (recommended)
./scripts/local-ci.sh --fast

# Full CI validation before push
./scripts/local-ci.sh

# Check test pyramid only
./scripts/local-ci.sh --pyramid

# Validate test markers only
./scripts/local-ci.sh --markers
```

### Test Pyramid Monitoring
```bash
# View pyramid report
python scripts/testing/test-pyramid-monitor-fast.py

# Generate JSON report
python scripts/testing/test-pyramid-monitor-fast.py --format json

# Generate HTML report
python scripts/testing/test-pyramid-monitor-fast.py --format html -o report.html

# Save historical data
python scripts/testing/test-pyramid-monitor-fast.py --save-history
```

### Test Marker Validation
```bash
# Validate all tests
python scripts/testing/validate-test-markers.py --all

# Validate specific files
python scripts/testing/validate-test-markers.py tests/test_example.py

# Verbose output
python scripts/testing/validate-test-markers.py --all --verbose
```

## Test Markers

### Pyramid Markers (Required)
Every test must have one of:
- `@pytest.mark.unit` - Fast, isolated unit tests (70% target)
- `@pytest.mark.integration` - Tests with external dependencies (20% target)
- `@pytest.mark.e2e` - End-to-end workflow tests (10% target)

### Speed Markers (Recommended)

| Category | Threshold | Marker | Use Case |
|----------|-----------|--------|----------|
| **Fast** | < 100ms | `@pytest.mark.fast` | Pre-commit, watch mode, rapid feedback |
| **Medium** | 100ms - 1s | `@pytest.mark.medium` | Standard CI runs |
| **Slow** | > 1s | `@pytest.mark.slow` | Nightly builds, thorough testing |

## Quick Commands

### Run Tests by Speed

```bash
# Fast tests only (< 100ms) - Quick feedback
./scripts/testing/run-fast-tests.sh
# OR
pytest -m "fast" tests/ -q --tb=short --no-cov

# Medium tests only (100ms - 1s)
./scripts/testing/run-by-speed.sh medium

# Slow tests only (> 1s)
./scripts/testing/run-by-speed.sh slow

# All except slow tests (most common for CI)
./scripts/testing/run-by-speed.sh not-slow
# OR
pytest -m "not slow" tests/ -v

# Fast and medium combined
./scripts/testing/run-by-speed.sh all-fast-medium
# OR
pytest -m "fast or medium" tests/
```

### Analysis and Reporting

```bash
# Generate test speed distribution report
python scripts/testing/test-speed-report.py tests/unit/
python scripts/testing/test-speed-report.py tests/integration/
python scripts/testing/test-speed-report.py tests/

# Add speed markers to tests automatically (dry run first)
python scripts/testing/add-speed-markers.py --dry-run
python scripts/testing/add-speed-markers.py --test-path tests/unit/
python scripts/testing/add-speed-markers.py  # All tests
```

### Check Current Markers

```bash
# Count tests by marker
pytest tests/unit/ -m "fast" --collect-only -q
pytest tests/unit/ -m "medium" --collect-only -q
pytest tests/unit/ -m "slow" --collect-only -q

# List all tests with a specific marker
pytest tests/ -m "slow" --collect-only -v
```

## CI Integration Examples

### Pre-commit Hook
```bash
# Fast tests only for quick validation
pytest -m "fast" tests/ -q --tb=short --no-cov
```

### Standard CI Run
```bash
# All tests except slow ones
pytest -m "not slow" tests/ -v --cov=src --cov-report=xml
```

### Nightly Build
```bash
# All tests including slow ones
pytest tests/ -v --cov=src --cov-report=html
```

### Watch Mode
```bash
# With pytest-watch
ptw -m "fast" tests/
```

## Marker Combinations

```bash
# Unit tests that are fast
pytest -m "unit and fast" tests/unit/

# Integration tests that are not slow
pytest -m "integration and not slow" tests/integration/

# Knowledge tests that are medium or fast
pytest -m "knowledge and (fast or medium)" tests/
```

## Scripts Overview

### Quality Gate Scripts

#### validate-test-markers.py
Validates that all tests have proper pyramid markers.

**Features**:
- Scans test files for missing markers
- Detailed violation reports
- Pre-commit hook integration
- Bypass support for exceptions

**Usage**:
```bash
python scripts/testing/validate-test-markers.py --all --verbose
```

#### test-pyramid-monitor-fast.py
Fast test pyramid analysis using file parsing.

**Features**:
- Calculates pyramid score (0-10)
- Distribution analysis
- Multiple output formats
- Historical tracking
- Recommendations

**Usage**:
```bash
python scripts/testing/test-pyramid-monitor-fast.py
python scripts/testing/test-pyramid-monitor-fast.py --format json
```

#### local-ci.sh
Comprehensive local CI validation.

**Features**:
- Pyramid score checking
- Marker validation
- Test execution by type
- Fast and full modes
- Color-coded output

**Usage**:
```bash
./scripts/local-ci.sh --fast
./scripts/local-ci.sh
```

### Speed Analysis Scripts

#### test-speed-report.py
Analyzes test execution times and generates comprehensive reports.

**Features**:
- Runs all tests with timing
- Categorizes by speed
- Visual distribution charts
- JSON export
- Top slowest tests per category

### run-fast-tests.sh
Quick runner for fast tests only.

**Features**:
- Runs fast unit tests
- Runs fast integration tests
- Color-coded output
- No coverage for speed

### run-by-speed.sh
Flexible test runner with speed filtering.

**Categories**:
- fast
- medium
- slow
- not-slow
- all-fast-medium

### add-speed-markers.py
Automatically adds speed markers to test files.

**Features**:
- Measures actual test times
- Adds appropriate markers
- Dry-run mode
- File-by-file summary

## Current Statistics

### Test Distribution (as of implementation)
- **Total Tests**: 2,771
- **Fast Tests**: 658 (23.7%)
- **Medium Tests**: 5 (0.2%)
- **Slow Tests**: 4 (0.1%)
- **Not Yet Marked**: 2,104 (75.9%)

### Performance Impact
- **Fast Tests Only**: ~10-15 seconds
- **Fast + Medium**: ~30-45 seconds
- **All Tests**: ~2-3 minutes

## Next Steps

1. **Mark Remaining Tests**:
   ```bash
   python scripts/testing/add-speed-markers.py
   ```

2. **Update CI Pipeline**: Add speed-based test stages

3. **Developer Workflow**: Use fast tests for rapid feedback

4. **Nightly Builds**: Run complete suite including slow tests

## Quality Gate Thresholds

- **Minimum Pyramid Score**: 7.0/10.0
- **Target Distribution**: 70% unit, 20% integration, 10% e2e
- **Slow Test Threshold**: >1000ms
- **Slow Test Warning**: >10 slow tests

## Help

For detailed documentation, see:
- `docs/testing/QUALITY_GATES.md` - Complete quality gates guide
- `docs/testing/TEST_PYRAMID_GUIDE.md` - Test pyramid best practices
- `pytest.ini` - Marker definitions
- `.github/workflows/ci.yml` - CI pipeline configuration
