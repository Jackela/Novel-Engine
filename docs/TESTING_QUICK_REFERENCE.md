# Testing Quick Reference

*Last Updated: 2025-11-02*
*Version: 2.1 - Now with Parallel Execution Support*

## Running Tests

### Recommended (Standardized Scripts)

**Parallel Execution (Default - 60-70% Faster)**:
```bash
# Windows
powershell.exe -ExecutionPolicy Bypass -File scripts/run_pytest.ps1

# Linux/WSL/macOS
bash scripts/run_pytest.sh

# Note: Scripts now use -n auto for parallel execution
# Auto-detects CPU count for optimal performance
```

**Serial Execution (For Debugging)**:
```bash
# Windows
powershell.exe -ExecutionPolicy Bypass -File scripts/run_pytest.ps1 -n 0

# Linux/WSL/macOS
bash scripts/run_pytest.sh -n 0
```

### Common Test Commands

```bash
# Run all tests
scripts/run_pytest.ps1

# Run specific test directory
scripts/run_pytest.ps1 tests/unit/
scripts/run_pytest.ps1 tests/integration/bridges/

# Run specific test file
scripts/run_pytest.ps1 tests/unit/contexts/ai/domain/test_llm_provider_interface.py

# Run specific test function
scripts/run_pytest.ps1 tests/unit/test_schemas.py::test_character_action_validation

# Run with pattern matching
scripts/run_pytest.ps1 -k "test_bridge"
scripts/run_pytest.ps1 -k "not test_director_refactored"

# Verbose output
scripts/run_pytest.ps1 -v
scripts/run_pytest.ps1 -vv  # Extra verbose

# Stop on first failure
scripts/run_pytest.ps1 -x

# Stop after N failures
scripts/run_pytest.ps1 --maxfail=5

# Show test durations
scripts/run_pytest.ps1 --durations=10
```

### Test Markers

```bash
# Run only unit tests
scripts/run_pytest.ps1 -m unit

# Run only integration tests
scripts/run_pytest.ps1 -m integration

# Skip slow tests
scripts/run_pytest.ps1 -m "not slow"

# Run specific categories
scripts/run_pytest.ps1 -m "character or narrative"
```

## Test Configuration

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
addopts = -q -rA --color=no
timeout = 45
timeout_method = thread
timeout_func_only = False
faulthandler_timeout = 60
junit_family = xunit2
log_cli = false
```

### Environment Variables

```bash
# Disable plugin auto-discovery (set in scripts)
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

# Python buffering (set in scripts)
PYTHONUNBUFFERED=1
PYTHONIOENCODING=UTF-8
```

## Test Statistics

- **Total Tests**: 2438
- **Unit Tests**: ~1690
- **Integration Tests**: ~75
- **Contract Tests**: 2

### Coverage by Module

| Module | Tests | Status |
|--------|-------|--------|
| `contexts/ai/domain` | 86 | ✅ All passing |
| `contexts/character` | 18 | ✅ 15 passing, 3 edge cases |
| `integration/bridges` | 18 | ✅ All passing |
| `integration/interactions` | 12 | ✅ All passing |
| `contract` | 2 | ✅ All passing |

## Common Issues & Solutions

### Issue: Tests Timeout

**Solution**: Use standardized scripts with proper timeout handling

```bash
# Good
scripts/run_pytest.ps1 --maxfail=10

# Avoid
pytest  # May use wrong Python/config
```

### Issue: Async Tests Fail

**Solution**: Ensure `pytest-asyncio` is installed and configured

```bash
pip install pytest-asyncio
# Scripts automatically load asyncio plugin
```

### Issue: Process/Port Cleanup

**Solution**: See `PROCESS_CLEANUP_RULES.md` or use pre-run cleanup

```bash
# Manual port cleanup
npx kill-port 3000 3001 8000 8003
```

### Issue: Import Errors

**Solution**: Ensure using project virtual environment

```bash
# Verify correct Python
which python  # Should point to .venv/bin/python
where python  # Windows

# Re-activate if needed
.venv/Scripts/activate  # Windows
source .venv/bin/activate  # Linux/macOS
```

## Test File Organization

```
tests/
├── conftest.py              # Shared fixtures
├── contract/                # API contract tests
│   └── test_cache_api_contract.py
├── integration/             # Integration tests
│   ├── api/                # API integration
│   ├── bridges/            # Multi-agent bridges
│   ├── core/               # Core components
│   └── interactions/       # Interaction engine
└── unit/                    # Unit tests
    ├── agents/             # Agent tests
    ├── contexts/           # Context tests
    │   ├── ai/            # AI domain
    │   └── character/     # Character domain
    └── ...
```

## Debugging Tests

### Run Single Test with Full Output

```bash
scripts/run_pytest.ps1 tests/unit/test_specific.py::test_function -vvs
```

### Show Full Traceback

```bash
scripts/run_pytest.ps1 --tb=long
scripts/run_pytest.ps1 --tb=short  # Default
scripts/run_pytest.ps1 --tb=line   # Minimal
```

### Collect Tests Without Running

```bash
scripts/run_pytest.ps1 --collect-only
scripts/run_pytest.ps1 --collect-only -q  # Quiet
```

### Debug Mode

```bash
# Enter debugger on failure
scripts/run_pytest.ps1 --pdb

# Enter debugger on error
scripts/run_pytest.ps1 --pdbcls=IPython.terminal.debugger:TerminalPdb
```

## Test Reports

### JUnit XML Report

Generated automatically at `pytest-report.xml`

```bash
# View summary
cat pytest-report.xml | grep testsuite
```

### Coverage Report

```bash
# Generate coverage report
scripts/run_pytest.ps1 --cov=src --cov-report=html

# View in browser
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run Tests
  run: bash scripts/run_pytest.sh --maxfail=10
```

### Local Pre-commit

```bash
# Run tests before commit
scripts/run_pytest.ps1 tests/unit/ -x
```

## Additional Resources

- **Full Testing Guide**: `docs/TESTING.md`
- **Test Structure**: `docs/TESTING_STRUCTURE.md`
- **Process Cleanup**: `PROCESS_CLEANUP_RULES.md`
- **Pytest Docs**: https://docs.pytest.org/
