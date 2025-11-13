#!/usr/bin/env bash
# CI/CD Local Validation Script
# Purpose: Run formatter, lint, and test checks equivalent to GitHub Actions QA pipeline
# Usage: bash scripts/validate_ci_locally.sh

set -euo pipefail

echo "🔍 CI/CD Local Validation for Novel-Engine"
echo "=========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PY_BIN=${PY_BIN:-python3}
VENV_DIR=${VENV_DIR:-.venv-ci}
DEFAULT_FLAKE8_TARGETS=("config_loader.py" "contexts/knowledge" "src/api")
DEFAULT_MYPY_TARGETS=("contexts/knowledge/application/use_cases/retrieve_agent_context.py")

if [[ -n "${FLAKE8_TARGETS:-}" ]]; then
    read -r -a FLAKE8_PATHS <<< "$FLAKE8_TARGETS"
else
    FLAKE8_PATHS=("${DEFAULT_FLAKE8_TARGETS[@]}")
fi

if [[ -n "${MYPY_TARGETS:-}" ]]; then
    read -r -a MYPY_PATHS <<< "$MYPY_TARGETS"
else
    MYPY_PATHS=("${DEFAULT_MYPY_TARGETS[@]}")
fi

echo "📋 Checking Python version..."
if ! command -v "$PY_BIN" >/dev/null 2>&1; then
    echo -e "${RED}❌ ${PY_BIN} not found on PATH${NC}"
    exit 1
fi
python_version=$("$PY_BIN" --version 2>&1 | awk '{print $2}')
if [[ ! "$python_version" =~ ^3\.1[1-9] ]]; then
    echo -e "${RED}❌ Python 3.11+ required for local validation${NC}"
    echo -e "   ${YELLOW}Found: Python $python_version${NC}"
    echo -e "   ${YELLOW}Install: https://www.python.org/downloads/${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $python_version detected${NC}"
echo ""

if ! "$PY_BIN" -m venv --help >/dev/null 2>&1; then
    echo -e "${RED}❌ python3-venv is required. Install with:${NC}"
    echo -e "   ${YELLOW}sudo apt-get install python3.11-venv${NC}"
    exit 1
fi

echo "📦 Installing dependencies..."
if [ ! -d "$VENV_DIR" ]; then
    echo "   creating virtual environment at $VENV_DIR"
    "$PY_BIN" -m venv "$VENV_DIR"
fi
VENV_PY="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"
"$VENV_PIP" install --upgrade pip --quiet
"$VENV_PIP" install -r requirements.txt --quiet
"$VENV_PIP" install pytest pytest-cov coverage httpx pytest-timeout pytest-asyncio black isort flake8 mypy playwright pytest-html --quiet
"$VENV_PY" -m playwright install chromium >/dev/null 2>&1 
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

echo "🧹 Running formatting and lint checks..."
set +e
"$VENV_PY" -m black --check src tests ai_testing scripts
BLACK_EXIT=$?
"$VENV_PY" -m isort --check-only src tests ai_testing scripts
ISORT_EXIT=$?
echo "   flake8 targets: ${FLAKE8_PATHS[*]}"
"$VENV_PY" -m flake8 "${FLAKE8_PATHS[@]}"
FLAKE_EXIT=$?
echo "   mypy targets: ${MYPY_PATHS[*]}"
"$VENV_PY" -m mypy "${MYPY_PATHS[@]}" --ignore-missing-imports
MYPY_EXIT=$?
set -e

if [ $BLACK_EXIT -ne 0 ] || [ $ISORT_EXIT -ne 0 ] || [ $FLAKE_EXIT -ne 0 ] || [ $MYPY_EXIT -ne 0 ]; then
    echo -e "${RED}❌ Formatting/linting checks failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Formatting/lint checks passed${NC}"
echo ""

echo "🧪 Running tests with coverage (this matches GitHub Actions exactly)..."
"$VENV_PY" -m pytest \
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

# Capture exit code
test_exit_code=$?

echo ""
echo "=========================================="
if [ $test_exit_code -eq 0 ]; then
    echo -e "${GREEN}✅ Validation PASSED${NC}"
    echo -e "${GREEN}   All tests passed and coverage meets threshold${NC}"
    echo -e "${GREEN}   Safe to push to GitHub${NC}"
else
    echo -e "${RED}❌ Validation FAILED${NC}"
    echo -e "${RED}   Fix issues before pushing to GitHub${NC}"
    echo ""
    echo "Common issues:"
    echo "  - Formatter or lint failures (see above)."
    echo "  - Test failures: check pytest output."
    echo "  - Coverage shortfall: verify .coveragerc and add tests."
fi
echo "=========================================="

exit $test_exit_code
