# Implementation Plan: CI/CD Coverage Alignment and Test Configuration Synchronization

**Branch**: `001-cicd-coverage-fix` | **Date**: 2025-10-28 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/001-cicd-coverage-fix/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

**Primary Requirement**: Align CI/CD test configuration and coverage requirements between local development environment (pytest, act CLI) and GitHub Actions to prevent undetected failures and reduce CI feedback time from 30+ minutes to under 3 minutes.

**Technical Approach**:
1. Consolidate coverage threshold (30%) to single source file (pytest.ini)
2. Standardize on Python 3.11 (eliminate 4-version matrix testing)
3. Create local validation script that exactly replicates GitHub Actions test execution
4. Remove permissive error handling from act CLI workflows
5. Fix 20 critical blocking test failures (13 security + 7 persona core)
6. Update all workflow configurations to read from single source

## Technical Context

**Language/Version**: Python 3.11 (standardized from PYTHON_VERSION env variable)  
**Primary Dependencies**: pytest, pytest-cov, coverage.py, act CLI, Black, isort, Bandit, Safety  
**Storage**: N/A (configuration and test fixes only)  
**Testing**: pytest with coverage.py for measurement, act CLI for local GitHub Actions simulation  
**Target Platform**: Cross-platform (Windows, macOS, Linux) local development + GitHub Actions (ubuntu-latest)  
**Project Type**: Single project (existing Python codebase with test suite)  
**Performance Goals**: 
- Quality Assurance Pipeline completes in <25 minutes (currently >30 min timeout)
- Local validation completes in <3 minutes (fast feedback)
- Coverage calculation overhead <10 seconds

**Constraints**: 
- Cannot reduce coverage below 26.42% (current actual)
- Must maintain cross-platform compatibility for local validation
- GitHub Actions free tier compute time limits (30-minute hard timeout)
- Must use industry-standard tools (pytest-cov, coverage.py) - no custom implementations
- Single source of truth for coverage threshold to prevent drift

**Scale/Scope**: 
- ~40,347 code statements in src/
- 39 test failures to triage (20 critical to fix)
- 4 GitHub Actions workflows to update
- 3 test execution environments to synchronize (local, act CLI, GitHub Actions)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Constitution Status**: This project does not have a populated constitution file. Using general software engineering principles for gate evaluation.

### General Principles Applied

**Principle: Simplicity & Maintainability**
- ✅ **PASS**: Solution simplifies configuration (single source file, single Python version)
- ✅ **PASS**: Removes complexity (eliminates 4-version matrix, consolidates workflows)

**Principle: Test-First Development**
- ✅ **PASS**: Feature focuses on test infrastructure improvements
- ✅ **PASS**: Includes fixing existing test failures before adding new features

**Principle: Configuration as Code**
- ✅ **PASS**: All configuration stored in version-controlled files (pytest.ini, .github/workflows/)
- ✅ **PASS**: Single source of truth prevents manual sync errors

**Principle: Developer Experience**
- ✅ **PASS**: Fast local validation (<3 min) improves productivity
- ✅ **PASS**: Clear error messages and categorized failures aid debugging

**No violations detected** - proceeding to Phase 0 research.

## Project Structure

### Documentation (this feature)

```text
specs/001-cicd-coverage-fix/
├── spec.md              # Feature specification (✅ complete)
├── plan.md              # This file (✅ in progress)
├── research.md          # Phase 0 output (⏳ next)
├── data-model.md        # Phase 1 output (N/A - no data entities)
├── quickstart.md        # Phase 1 output (⏳ pending)
├── contracts/           # Phase 1 output (N/A - no API contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

**Current Structure** (existing project):
```text
.github/
├── workflows/
│   ├── quality_assurance.yml      # ⚠️ UPDATE: Remove matrix, set Python 3.11
│   ├── local-test-validation.yml  # ⚠️ UPDATE: Remove permissive error handling
│   ├── test-validation.yml        # ⚠️ UPDATE: Add coverage check
│   └── ci.yml                      # ℹ️ VERIFY: Already uses Python 3.11

src/                                # Existing source code
├── core/
├── contexts/
├── api/
├── security/                       # ⚠️ FIX: 13 security test failures
└── agents/                         # ⚠️ FIX: 7 persona core test failures

tests/                              # Existing test suite
├── unit/
├── integration/
├── security/
└── performance/

scripts/
├── validate_ci_locally.sh         # ➕ CREATE: New local validation script

pytest.ini                          # ⚠️ UPDATE: Add coverage config (single source)
.coveragerc                         # ⚠️ ALTERNATIVE: Or use this as single source
README.md                           # ⚠️ UPDATE: Document coverage threshold
```

**Structure Decision**: This is a configuration and test-fixing feature for an existing single-project Python codebase. No new source structure needed - only updates to:
1. Workflow YAML files (4 files)
2. Test configuration (pytest.ini or .coveragerc)
3. Local validation script (new shell script)
4. Test files with failures (20 files in tests/)
5. Documentation (README)

## Complexity Tracking

> No constitution violations detected - this section is not applicable.

---

## Phase 0: Research & Technology Decisions

### Research Tasks

#### R1: Coverage Configuration Best Practices
**Question**: Should coverage threshold be in pytest.ini or .coveragerc for single source of truth?

**Decision**: Use `.coveragerc` as single source
**Rationale**:
- Dedicated coverage configuration file (clear separation of concerns)
- Supports both pytest-cov and direct coverage.py usage
- Can be referenced by GitHub Actions workflows via `--cov-config` parameter
- Industry standard for Python coverage configuration

**Alternatives Considered**:
- `pytest.ini`: Would work but mixes pytest general config with coverage specifics
- `pyproject.toml`: Modern approach but adds complexity if not already using it

**Implementation**:
```ini
# .coveragerc (single source of truth)
[run]
source = src
omit = 
    */tests/*
    */examples/*
    */demos/*
    */scripts/*

[report]
fail_under = 30
precision = 2
show_missing = true
skip_covered = false

[html]
directory = htmlcov
```

---

#### R2: Local Validation Script Approach
**Question**: Should local validation script be shell script, Python script, or Makefile target?

**Decision**: Cross-platform shell scripts (bash + PowerShell)
**Rationale**:
- Matches GitHub Actions workflow syntax (bash commands)
- Cross-platform support via dual scripts (validate_ci_locally.sh for bash, validate_ci_locally.ps1 for PowerShell)
- No Python environment needed to run validation (validates Python environment)
- Easy to maintain alongside workflow YAML files

**Alternatives Considered**:
- Pure Python script: Requires Python to be working before validating Python setup
- Makefile: Not standard on Windows, adds dependency
- npm scripts in package.json: Project is Python-first, not Node.js

**Implementation**:
```bash
#!/usr/bin/env bash
# scripts/validate_ci_locally.sh
set -euo pipefail

echo "🔍 CI/CD Local Validation"
echo "========================="

# Check Python version
python_version=$(python --version 2>&1 | awk '{print $2}')
if [[ ! "$python_version" =~ ^3\.11 ]]; then
    echo "❌ Python 3.11 required, found $python_version"
    exit 1
fi

# Run exact CI commands
echo "📦 Installing dependencies..."
pip install -r requirements.txt
pip install pytest pytest-cov coverage httpx pytest-timeout

echo "🧪 Running tests with coverage..."
python -m pytest \
  --cov=src \
  --cov-config=.coveragerc \
  --cov-report=xml \
  --cov-report=html \
  --cov-report=term-missing \
  --junitxml=test-results.xml \
  --maxfail=10 \
  -v \
  --tb=short \
  --durations=10

echo "✅ Validation complete"
```

---

#### R3: Test Failure Categorization Strategy
**Question**: How should 39 test failures be prioritized for fixing?

**Decision**: Fix blocking failures only (13 security + 7 persona core = 20 tests)
**Rationale**:
- Security failures block quality gates (critical path)
- Persona core failures block core functionality (critical path)
- Other 19 failures are non-blocking (can be deferred)
- Focus delivers 80% value with 20% effort (Pareto principle)

**Categories Identified**:
1. **Blocking - Security Framework** (13 failures): `tests/security/test_comprehensive_security.py`
   - SecurityHeaders.get_header attribute error
   - RateLimit import error
   - Password length validation
   - Authentication fixture issues

2. **Blocking - Persona Core** (7 failures): `tests/test_persona_core.py`
   - AgentIdentity initialization signature mismatch
   - PersonaCore attribute errors (is_active, activate, read_character_file)
   - Event bus integration issues

3. **Non-Blocking - Quality Framework** (6 failures): `tests/test_quality_framework.py`
   - Character name setter attribute errors
   - Orchestrator startup failures

4. **Non-Blocking - Error Handler** (3 failures): `tests/test_error_handler.py`
   - Error category detection mismatches
   - Recovery strategy mismatches

5. **Non-Blocking - Data Models** (2 failures): `tests/test_data_models.py`
   - Sacred validation assertion errors

**Alternatives Considered**:
- Fix all 39 failures: Too time-consuming, delays feature delivery
- Fix only coverage-blocking failures: Wouldn't address CI timeout issues

---

#### R4: Act CLI Workflow Alignment
**Question**: How to make act CLI workflows match GitHub Actions exactly?

**Decision**: Remove all permissive error handling (`|| echo`, `continue-on-error: true`)
**Rationale**:
- Permissive handling masks real failures, defeating purpose of local validation
- GitHub Actions workflows don't use permissive handling in production
- Strict failures provide accurate feedback to developers

**Specific Changes**:
```yaml
# BEFORE (local-test-validation.yml)
- name: Run tests
  run: |
    python -m pytest tests/unit/core/ -v --tb=short || echo "⚠️ Tests failed"

# AFTER (local-test-validation.yml)
- name: Run tests
  run: |
    python -m pytest \
      --cov=src \
      --cov-config=.coveragerc \
      --junitxml=test-results.xml \
      -v \
      --tb=short
  # No permissive error handling - fails properly
```

---

#### R5: Python Version Enforcement
**Question**: How to ensure developers use Python 3.11 locally?

**Decision**: Add Python version check to local validation script + document in README
**Rationale**:
- Validation script checks version before running tests (fail fast)
- README documents requirement prominently
- CI workflows already enforce Python 3.11

**Implementation**:
```bash
# In validate_ci_locally.sh
python_version=$(python --version 2>&1 | awk '{print $2}')
if [[ ! "$python_version" =~ ^3\.11 ]]; then
    echo "❌ Python 3.11 required for local validation"
    echo "   Found: Python $python_version"
    echo "   Install: https://www.python.org/downloads/"
    exit 1
fi
```

---

### Research Summary

All technical decisions resolved:
- ✅ Coverage config: `.coveragerc` (single source)
- ✅ Local validation: Dual shell scripts (bash + PowerShell)
- ✅ Test prioritization: 20 blocking failures only
- ✅ Act CLI: Remove permissive error handling
- ✅ Python enforcement: Version check + documentation

**Output File**: `research.md` (complete)

---

## Phase 1: Design & Contracts

### Data Model

**N/A** - This feature does not introduce new data entities. It works with existing:
- Configuration files (.coveragerc, pytest.ini, *.yml)
- Test results (XML/HTML reports)
- Coverage data (coverage.py database)

No `data-model.md` needed.

### API Contracts

**N/A** - This feature does not introduce new API endpoints. It updates:
- CI/CD workflow contracts (YAML schema)
- Shell script interfaces (command-line arguments)
- Configuration file formats (INI syntax)

No `/contracts/` directory needed.

### Quick Start Guide

**Purpose**: Help developers adopt new local validation workflow

**Content**: See `quickstart.md` (Phase 1 output)

### Agent Context Update

Will run `.specify/scripts/powershell/update-agent-context.ps1 -AgentType claude` after quickstart creation.

---

## Next Steps

1. ✅ **Phase 0 Complete**: Research decisions documented above
2. ⏳ **Phase 1 In Progress**: Creating quickstart.md
3. ⏳ **Phase 2 Pending**: Run `/speckit.tasks` to generate implementation tasks

**Files Generated**:
- ✅ `plan.md` (this file)
- ✅ `research.md` (embedded above)
- ⏳ `quickstart.md` (next)
- ⏳ `tasks.md` (via `/speckit.tasks`)
