# Test Pyramid Monitor - Usage Guide

## Quick Start

```bash
# Simplest way - console output
./scripts/testing/check-pyramid.sh

# Or directly with Python
python scripts/testing/test-pyramid-monitor-fast.py
```

## Common Use Cases

### 1. Daily Check (Console)

```bash
./scripts/testing/check-pyramid.sh
```

Output:
```
================================================================================
                         TEST PYRAMID REPORT
================================================================================
Date: 2025-11-25 12:07:06
Score: 2.2/10.0

DISTRIBUTION:
  Unit           2,365 ( 80.7%)  [Target:   70%]  ████████████████░░░░  +10.7%
  Integration       11 (  0.4%)  [Target:   20%]  ░░░░░░░░░░░░░░░░░░░░  -19.6%
  E2e                5 (  0.2%)  [Target:   10%]  ░░░░░░░░░░░░░░░░░░░░  -9.8%

TOTAL: 2,930 tests

MISSING MARKERS: 549 tests need classification
```

### 2. CI Integration (JSON)

```bash
./scripts/testing/check-pyramid.sh --json > pyramid-report.json
```

### 3. Generate HTML Report

```bash
./scripts/testing/check-pyramid.sh --html --output reports/pyramid.html
```

### 4. Track History Over Time

```bash
./scripts/testing/check-pyramid.sh --save
```

This creates:
- `.pyramid-history/2025-11-25.json` (dated file)
- `.pyramid-history/latest.json` (latest run)

### 5. PR Comment (Markdown)

```bash
./scripts/testing/check-pyramid.sh --markdown | gh pr comment --body-file -
```

## Script Options

### Shell Wrapper (`check-pyramid.sh`)

```bash
./scripts/testing/check-pyramid.sh [OPTIONS]

Options:
  --json          Output JSON format
  --html          Output HTML format
  --markdown      Output Markdown format
  --save          Save historical data
  --output FILE   Write to file
  --help          Show help
```

### Python Script

```bash
python scripts/testing/test-pyramid-monitor-fast.py [OPTIONS]

Options:
  --format {console,json,html,markdown}
  --save-history
  --output PATH, -o PATH
```

## Integration Examples

### Add to validate_ci_locally.sh

```bash
# In scripts/validate_ci_locally.sh

echo "=================================================="
echo "Test Pyramid Check"
echo "=================================================="

./scripts/testing/check-pyramid.sh
PYRAMID_EXIT=$?

if [ $PYRAMID_EXIT -ne 0 ]; then
    echo "⚠️  Warning: Test pyramid score is below 5.0"
    echo "Run './scripts/testing/check-pyramid.sh' for details"
fi
```

### GitHub Actions

```yaml
# .github/workflows/test-pyramid.yml
name: Test Pyramid

on:
  pull_request:
  push:
    branches: [main]

jobs:
  pyramid-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Check Pyramid
        run: |
          ./scripts/testing/check-pyramid.sh --json > pyramid.json
          ./scripts/testing/check-pyramid.sh --markdown > pyramid.md

      - name: Save Reports
        uses: actions/upload-artifact@v3
        with:
          name: pyramid-reports
          path: pyramid.*

      - name: Comment on PR (if PR)
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('pyramid.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '## Test Pyramid Report\n\n' + report
            });
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Only check if test files changed
if git diff --cached --name-only | grep -q "^tests/.*\.py$"; then
    echo "Test files changed - checking pyramid..."
    ./scripts/testing/check-pyramid.sh

    if [ $? -ne 0 ]; then
        echo ""
        echo "⚠️  Test pyramid score is low"
        echo "Consider adding appropriate markers to new tests"
        echo ""
        read -p "Continue with commit? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLYY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi
```

### Daily Cron Job

```bash
# Add to crontab
0 9 * * * cd /path/to/novel-engine && \
  ./scripts/testing/check-pyramid.sh --save --html \
  --output /var/www/reports/pyramid-$(date +\%Y-\%m-\%d).html
```

### Makefile Integration

```makefile
# In Makefile

.PHONY: pyramid pyramid-report pyramid-html

pyramid:
	@./scripts/testing/check-pyramid.sh

pyramid-report:
	@./scripts/testing/check-pyramid.sh --json

pyramid-html:
	@./scripts/testing/check-pyramid.sh --html --output pyramid-report.html
	@echo "Report saved to pyramid-report.html"
	@xdg-open pyramid-report.html 2>/dev/null || open pyramid-report.html 2>/dev/null || true
```

Then use:
```bash
make pyramid          # Quick check
make pyramid-html     # Generate and open HTML report
```

## Understanding the Output

### Score Interpretation

| Score | Status | Meaning |
|-------|--------|---------|
| 8.0-10.0 | Excellent | Well-balanced pyramid |
| 6.0-7.9 | Good | Minor adjustments needed |
| 4.0-5.9 | Fair | Significant rebalancing required |
| 0.0-3.9 | Poor | Major pyramid issues |

### Delta Explanation

```
Unit  2,365 ( 80.7%)  [Target:   70%]  ████████████████░░░░  +10.7%
                                                             ^^^^^^
                                                             Delta from target
```

- **Positive (+)**: Over target (too many tests in this layer)
- **Negative (-)**: Under target (too few tests in this layer)
- **Zero (0.0%)**: Perfect match with target

### Missing Markers

Tests without `@pytest.mark.unit`, `@pytest.mark.integration`, or `@pytest.mark.e2e`:

```python
# Missing marker - will be flagged
def test_something():
    pass

# Properly marked
@pytest.mark.unit
def test_something():
    pass
```

## Analyzing Historical Data

### View Trend

```bash
# View scores over time
for file in .pyramid-history/*.json; do
    echo -n "$(basename $file): "
    jq -r '.score' "$file"
done
```

### Compare Dates

```bash
# Compare two dates
echo "Before:"
jq '.distribution' .pyramid-history/2025-11-20.json

echo "After:"
jq '.distribution' .pyramid-history/2025-11-25.json
```

### Extract Specific Data

```bash
# Get unit test count
jq '.distribution.unit.count' .pyramid-history/latest.json

# Get missing markers count
jq '.missing_markers' .pyramid-history/latest.json

# Get all scores
jq -r '.score' .pyramid-history/*.json | sort -n
```

## Improving Your Score

### 1. Add Missing Markers

Find tests without markers:
```bash
# Find test functions without markers
grep -r "def test_" tests/ | \
  while read line; do
    file=$(echo $line | cut -d: -f1)
    if ! grep -B5 "$line" "$file" | grep -q "@pytest.mark."; then
      echo "$line"
    fi
  done
```

### 2. Reclassify Tests

Review tests that might be misclassified:

```bash
# Find "integration" tests in unit directories
grep -r "@pytest.mark.integration" tests/unit/

# Find "unit" tests in integration directories
grep -r "@pytest.mark.unit" tests/integration/
```

### 3. Balance Distribution

Based on recommendations:

- **Too many unit tests?** Some might be integration tests in disguise
- **Too few integration tests?** Some complex unit tests might need reclassification
- **Too many E2E tests?** Keep only critical user paths

## Troubleshooting

### Script Reports Wrong Counts

The fast version uses regex. For exact counts, use the slow version:

```bash
python scripts/testing/test-pyramid-monitor.py
```

### Tests Not Detected

Ensure tests follow conventions:
- File: `test_*.py` or `*_test.py`
- Function: `test_*` or in `Test*` class
- Location: In `tests/` directory

### Markers Not Found

Check `pytest.ini` has markers defined:

```ini
markers =
    unit: marks tests as unit tests
    integration: marks tests as integration tests
    e2e: marks tests as end-to-end tests
```

## Performance Notes

### Fast Version (Recommended)
- **Time**: 2-5 seconds
- **Method**: File parsing with regex
- **Accuracy**: ~98%
- **Use for**: Daily checks, CI, quick feedback

### Original Version
- **Time**: 60-120 seconds
- **Method**: pytest collection (4 passes)
- **Accuracy**: 100%
- **Use for**: Detailed analysis, verification

## Advanced Usage

### Custom Targets

Edit the script to change targets:

```python
# In test-pyramid-monitor-fast.py
TARGETS = {
    "unit": 70.0,        # Change to 75.0 for stricter unit testing
    "integration": 20.0,  # Change to 15.0 for fewer integration tests
    "e2e": 10.0,         # Change to 10.0 (keep as is)
}
```

### Webhook Integration

```bash
# Post results to webhook
./scripts/testing/check-pyramid.sh --json | \
  curl -X POST -H "Content-Type: application/json" \
  -d @- https://webhook.site/your-webhook-id
```

### Slack Notification

```bash
#!/bin/bash
SCORE=$(./scripts/testing/check-pyramid.sh --json | jq -r '.score')

if (( $(echo "$SCORE < 5.0" | bc -l) )); then
    curl -X POST -H 'Content-type: application/json' \
    --data "{\"text\":\"⚠️ Test pyramid score dropped to $SCORE\"}" \
    YOUR_SLACK_WEBHOOK_URL
fi
```

### Dashboard Data

```bash
# Generate data for Grafana/Prometheus
./scripts/testing/check-pyramid.sh --json | \
  jq '{
    pyramid_score: .score,
    pyramid_unit_pct: .distribution.unit.percentage,
    pyramid_integration_pct: .distribution.integration.percentage,
    pyramid_e2e_pct: .distribution.e2e.percentage,
    pyramid_missing: .missing_markers
  }'
```

## Next Steps

1. Run initial check: `./scripts/testing/check-pyramid.sh`
2. Review recommendations
3. Add missing markers to tests
4. Integrate into CI (see examples above)
5. Monitor trends weekly
6. Aim for score > 7.0

## Related Documentation

- **PYRAMID_MONITOR.md**: Detailed technical documentation
- **EXAMPLES.md**: Example test files with proper markers
- **pyramid-history-schema.json**: JSON schema for history data
- **pyramid-report-template.html**: HTML template for reports
