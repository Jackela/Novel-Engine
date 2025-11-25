# Test Pyramid Monitor

Automated monitoring system that tracks test distribution across the testing pyramid and reports against ideal targets.

## Overview

The Test Pyramid Monitor helps maintain a healthy test suite by:
- Tracking test distribution across unit/integration/e2e layers
- Comparing against ideal targets (70% unit, 20% integration, 10% e2e)
- Identifying tests missing pyramid markers
- Generating reports in multiple formats
- Tracking trends over time

## Files

### Main Scripts

1. **test-pyramid-monitor-fast.py** (Recommended)
   - Fast version that parses test files directly
   - Runs in 2-5 seconds
   - Ideal for CI/CD and quick checks
   - Uses regex to find test functions and markers

2. **test-pyramid-monitor.py**
   - Original version using pytest collection
   - More accurate but slower (60-120 seconds)
   - Uses pytest's native test collection
   - Better for detailed analysis

### Templates

3. **pyramid-report-template.html**
   - Beautiful HTML report template
   - Includes pyramid visualization (SVG)
   - Responsive design
   - Charts and progress bars

### History

4. **.pyramid-history/** directory
   - Stores historical data
   - JSON format for each date
   - `latest.json` for most recent run

## Usage

### Quick Start

```bash
# Console report (default)
python scripts/testing/test-pyramid-monitor-fast.py

# JSON output
python scripts/testing/test-pyramid-monitor-fast.py --format json

# HTML report
python scripts/testing/test-pyramid-monitor-fast.py --format html -o report.html

# Markdown report
python scripts/testing/test-pyramid-monitor-fast.py --format markdown

# Save history
python scripts/testing/test-pyramid-monitor-fast.py --save-history
```

### Command-Line Options

```
--format {console,json,html,markdown}
    Output format (default: console)

--save-history
    Save historical data to .pyramid-history/

--output PATH, -o PATH
    Output file (default: stdout)
```

### Exit Codes

- `0`: Success, score >= 5.0
- `1`: Warning, score < 5.0

## Report Formats

### Console (ASCII)

```
================================================================================
                         TEST PYRAMID REPORT
================================================================================
Date: 2025-11-25 12:04:55
Score: 2.2/10.0

DISTRIBUTION:
  Unit           2,365 ( 80.7%)  [Target:   70%]  ████████████████░░░░  +10.7%
  Integration       11 (  0.4%)  [Target:   20%]  ░░░░░░░░░░░░░░░░░░░░  -19.6%
  E2e                5 (  0.2%)  [Target:   10%]  ░░░░░░░░░░░░░░░░░░░░  -9.8%

TOTAL: 2,930 tests

MISSING MARKERS: 549 tests need classification

RECOMMENDATIONS:
  1. Add pyramid markers (unit/integration/e2e) to 549 uncategorized tests
  2. Reduce unit tests or reclassify them (currently +10.7% above target)
  3. Add more integration tests (currently 19.6% below target)
  4. Add more e2e tests (currently 9.8% below target)
================================================================================
```

### JSON

```json
{
  "timestamp": "2025-11-25T12:05:07.799518",
  "score": 2.24,
  "total_tests": 2930,
  "test_files_scanned": 204,
  "distribution": {
    "unit": {
      "count": 2365,
      "percentage": 80.72,
      "target": 70.0,
      "delta": 10.72
    },
    "integration": {
      "count": 11,
      "percentage": 0.38,
      "target": 20.0,
      "delta": -19.62
    },
    "e2e": {
      "count": 5,
      "percentage": 0.17,
      "target": 10.0,
      "delta": -9.83
    }
  },
  "missing_markers": 549,
  "recommendations": [...]
}
```

### Markdown

Perfect for GitHub comments and documentation:

```markdown
# Test Pyramid Report

**Date:** 2025-11-25 12:05:12
**Score:** 2.2/10.0

## Distribution

| Type | Count | Percentage | Target | Delta |
|------|-------|------------|--------|-------|
| Unit | 2,365 | 80.7% | 70% | +10.7% |
| Integration | 11 | 0.4% | 20% | -19.6% |
| E2e | 5 | 0.2% | 10% | -9.8% |

**Total:** 2,930 tests
```

### HTML

Beautiful visual report with:
- Pyramid visualization (SVG graphic)
- Color-coded deltas
- Responsive design
- Print-friendly

## Scoring System

### Score Calculation (0-10)

- **Perfect Pyramid**: 10.0 points
- **Deductions**:
  - 0.1 point per 1% deviation from targets
  - 0.2 point per 1% of uncategorized tests

### Target Distribution

| Layer | Target | Rationale |
|-------|--------|-----------|
| Unit | 70% | Fast, isolated, numerous |
| Integration | 20% | Verify component interactions |
| E2E | 10% | Critical user paths only |

### Score Ranges

- **8.0-10.0**: Excellent - Well-balanced pyramid
- **6.0-7.9**: Good - Minor adjustments needed
- **4.0-5.9**: Fair - Significant rebalancing required
- **0.0-3.9**: Poor - Major pyramid issues

## CI Integration

### GitHub Actions

```yaml
# .github/workflows/test-pyramid.yml
name: Test Pyramid Check

on:
  pull_request:
  push:
    branches: [main]

jobs:
  pyramid:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Generate Pyramid Report
        run: |
          python scripts/testing/test-pyramid-monitor-fast.py \
            --format markdown > pyramid-report.md
          python scripts/testing/test-pyramid-monitor-fast.py \
            --format json > pyramid-report.json
          python scripts/testing/test-pyramid-monitor-fast.py \
            --save-history

      - name: Comment on PR
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('pyramid-report.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: report
            });

      - name: Upload Reports
        uses: actions/upload-artifact@v3
        with:
          name: pyramid-reports
          path: |
            pyramid-report.*
            .pyramid-history/
```

### Local CI Script

Add to `scripts/validate_ci_locally.sh`:

```bash
# Test Pyramid Check
echo "Checking test pyramid distribution..."
python scripts/testing/test-pyramid-monitor-fast.py --format console
PYRAMID_EXIT=$?

if [ $PYRAMID_EXIT -ne 0 ]; then
    echo "⚠️  Test pyramid needs attention (score < 5.0)"
fi
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Check pyramid on significant test changes
if git diff --cached --name-only | grep -q "tests/.*\.py"; then
    echo "Checking test pyramid..."
    python scripts/testing/test-pyramid-monitor-fast.py --format console
fi
```

## Historical Tracking

### Data Format

```json
{
  "timestamp": "2025-11-25T12:05:16.056481",
  "score": 2.24,
  "total_tests": 2930,
  "distribution": {
    "unit": {"count": 2365, "percentage": 80.72},
    "integration": {"count": 11, "percentage": 0.38},
    "e2e": {"count": 5, "percentage": 0.17}
  },
  "missing_markers": 549
}
```

### Trend Analysis

```bash
# Compare last 7 days
for file in .pyramid-history/*.json; do
    echo "$file:"
    jq '.score' "$file"
done

# Plot trend
python scripts/testing/plot-pyramid-trends.py
```

## Recommendations

### Adding Missing Markers

Tests without `@pytest.mark.unit`, `@pytest.mark.integration`, or `@pytest.mark.e2e` are considered uncategorized.

```python
# Before
def test_user_login():
    pass

# After
@pytest.mark.integration
def test_user_login():
    pass
```

### Marker Guidelines

**Unit Tests** (`@pytest.mark.unit`):
- Test single functions/methods in isolation
- Use mocks for dependencies
- Fast (< 100ms)
- No I/O, database, or network

**Integration Tests** (`@pytest.mark.integration`):
- Test multiple components together
- May use real dependencies (database, etc.)
- Medium speed (100ms - 1000ms)
- Test component interactions

**E2E Tests** (`@pytest.mark.e2e`):
- Test complete user flows
- Full stack (API, database, etc.)
- Slow (> 1000ms)
- Critical paths only

## Troubleshooting

### Script is slow

Use the fast version:
```bash
python scripts/testing/test-pyramid-monitor-fast.py
```

### Incorrect counts

The fast version uses regex parsing. For exact counts, use:
```bash
python scripts/testing/test-pyramid-monitor.py
```

### Tests not detected

Ensure tests follow pytest conventions:
- Files: `test_*.py` or `*_test.py`
- Functions: `test_*` or `Test*` classes
- Located in `tests/` directory

### Missing markers not shown

Check that markers are defined in `pytest.ini`:
```ini
markers =
    unit: marks tests as unit tests
    integration: marks tests as integration tests
    e2e: marks tests as end-to-end tests
```

## Performance

### Fast Version
- Scans ~200 test files in 2-5 seconds
- Pure Python file parsing
- Regex-based test detection
- No pytest subprocess overhead

### Original Version
- Runs pytest collection 4 times
- Takes 60-120 seconds
- More accurate counts
- Uses pytest's native detection

## Maintenance

### Updating Targets

Edit the `TARGETS` dict in the script:

```python
TARGETS = {
    "unit": 70.0,
    "integration": 20.0,
    "e2e": 10.0,
}
```

### Customizing Scoring

Adjust penalties in `calculate_score()`:

```python
# Current: 0.1 point per 1% deviation
penalty = deviation * 0.1

# Make stricter: 0.2 point per 1%
penalty = deviation * 0.2
```

## Examples

### Daily Monitoring

```bash
# Add to cron
0 9 * * * cd /path/to/project && \
  python scripts/testing/test-pyramid-monitor-fast.py \
  --save-history --format html -o reports/pyramid-$(date +%F).html
```

### PR Comments

```bash
# Generate markdown for PR
python scripts/testing/test-pyramid-monitor-fast.py \
  --format markdown | gh pr comment --body-file -
```

### Dashboard Integration

```bash
# Generate JSON for dashboard
python scripts/testing/test-pyramid-monitor-fast.py \
  --format json | curl -X POST -d @- \
  https://dashboard.example.com/api/pyramid
```

## Contributing

To add a new output format:

1. Add format choice to argparse
2. Implement `generate_<format>_report()` method
3. Add format handling in `main()`
4. Update this documentation

## License

Same as parent project.
