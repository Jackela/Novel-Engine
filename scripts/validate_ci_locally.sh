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
MIN_PYRAMID_SCORE=${MIN_PYRAMID_SCORE:-5.5}
DEFAULT_FLAKE8_TARGETS=("src/core/config/config_loader.py" "src/contexts/knowledge" "src/api")
DEFAULT_MYPY_TARGETS=("src/contexts/knowledge/application/use_cases/retrieve_agent_context.py")

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
python_major=${python_version%%.*}
python_minor=$(echo "$python_version" | cut -d. -f2)
if [[ "$python_major" -ne 3 || "$python_minor" -lt 11 ]]; then
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

echo "🔒 Running security scan (CodeQL required)..."
REQUIRE_CODEQL=1 PY_BIN="$VENV_PY" bash scripts/codeql-local.sh
echo ""

echo "🧹 Running formatting and lint checks..."
FORMAT_PATHS=(src tests scripts)
if [ -d "ai_testing" ]; then
    FORMAT_PATHS+=("ai_testing")
fi
set +e
"$VENV_PY" -m black --check "${FORMAT_PATHS[@]}"
BLACK_EXIT=$?
"$VENV_PY" -m isort --check-only "${FORMAT_PATHS[@]}"
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

echo "🧪 Running backend CI gates (parity with GitHub Actions)..."
mkdir -p reports
export PYTHONPATH="$PWD:$PWD/src"

set +e
"$VENV_PY" scripts/testing/validate-test-markers.py --all --verbose
MARKERS_EXIT=$?

"$VENV_PY" scripts/testing/test-pyramid-monitor-fast.py --format json --save-history > pyramid-report.json
PYRAMID_EXIT=$?
if [ $PYRAMID_EXIT -eq 0 ]; then
  SCORE=$("$VENV_PY" - <<'PY'
import json
data=json.load(open("pyramid-report.json"))
print(data["score"])
PY
  )
  SCORE_OK=$("$VENV_PY" - <<PY
score=float("$SCORE")
minimum=float("$MIN_PYRAMID_SCORE")
print("1" if score >= minimum else "0")
PY
  )
  if [ "$SCORE_OK" -ne 1 ]; then
    echo -e "${RED}❌ Test pyramid score ($SCORE) below threshold ($MIN_PYRAMID_SCORE)${NC}"
    PYRAMID_EXIT=1
  fi
fi

"$VENV_PY" -m pytest -m "unit" --tb=short --durations=10 --junitxml=reports/unit-tests.xml
UNIT_EXIT=$?
"$VENV_PY" -m pytest -m "integration" --tb=short --durations=10 --junitxml=reports/integration-tests.xml
INTEGRATION_EXIT=$?
"$VENV_PY" -m pytest -m "e2e" --tb=short --durations=10 --junitxml=reports/e2e-tests.xml
E2E_EXIT=$?
"$VENV_PY" -m pytest -q tests/test_enhanced_bridge.py tests/test_character_system_comprehensive.py --junitxml=reports/smoke-tests.xml
SMOKE_EXIT=$?
set -e

test_exit_code=0
if [ $MARKERS_EXIT -ne 0 ] || [ $PYRAMID_EXIT -ne 0 ] || [ $UNIT_EXIT -ne 0 ] || [ $INTEGRATION_EXIT -ne 0 ] || [ $E2E_EXIT -ne 0 ] || [ $SMOKE_EXIT -ne 0 ]; then
    test_exit_code=1
fi

echo ""
echo "🌐 Running frontend CI checks..."
FRONTEND_DIR="frontend"
if [ -d "$FRONTEND_DIR" ]; then
    cd "$FRONTEND_DIR"
    if [ -f "package.json" ] && grep -q '"test"' package.json; then
        frontend_lint_exit=0
        frontend_typecheck_exit=0
        frontend_format_exit=0
        frontend_tokens_exit=0
        frontend_test_exit=0
        frontend_build_exit=0
        frontend_smoke_exit=0
        win_cmd=""
        if [ -x /mnt/c/Windows/System32/cmd.exe ]; then
            win_cmd="/mnt/c/Windows/System32/cmd.exe"
        elif command -v cmd.exe >/dev/null 2>&1; then
            win_cmd="cmd.exe"
        fi
        if grep -qi microsoft /proc/version 2>/dev/null && [ -n "$win_cmd" ]; then
            win_frontend_dir=$(wslpath -w "$PWD")
            "$win_cmd" /c "cd /d $win_frontend_dir && npm ci"
            "$win_cmd" /c "cd /d $win_frontend_dir && npm run lint:all --if-present"
            frontend_lint_exit=$?
            "$win_cmd" /c "cd /d $win_frontend_dir && npm run type-check --if-present"
            frontend_typecheck_exit=$?
            "$win_cmd" /c "cd /d $win_frontend_dir && npm run format:check --if-present"
            frontend_format_exit=$?
            "$win_cmd" /c "cd /d $win_frontend_dir && npm run build:tokens --if-present"
            frontend_tokens_exit=$?
            "$win_cmd" /c "cd /d $win_frontend_dir && npm run tokens:check --if-present"
            frontend_tokens_exit=$?
            "$win_cmd" /c "cd /d $win_frontend_dir && npm test --if-present --silent"
            frontend_test_exit=$?
            "$win_cmd" /c "cd /d $win_frontend_dir && npm run build --if-present"
            frontend_build_exit=$?
            "$win_cmd" /c "cd /d $win_frontend_dir && node scripts/test-cleanup.js"
            "$win_cmd" /c "cd /d $win_frontend_dir && set PYTHONPATH=..;..\\src && npm run test:e2e:smoke"
            frontend_smoke_exit=$?
        else
            npm ci
            npm run lint:all --if-present
            frontend_lint_exit=$?
            npm run type-check --if-present
            frontend_typecheck_exit=$?
            npm run format:check --if-present
            frontend_format_exit=$?
            npm run build:tokens --if-present
            frontend_tokens_exit=$?
            npm run tokens:check --if-present
            frontend_tokens_exit=$?
            npm test --if-present --silent
            frontend_test_exit=$?
            npm run build --if-present
            frontend_build_exit=$?
            PYTHONPATH="..:../src" npm run test:e2e:smoke
            frontend_smoke_exit=$?
        fi
        cd ..
        if [ $frontend_lint_exit -ne 0 ] || [ $frontend_typecheck_exit -ne 0 ] || [ $frontend_format_exit -ne 0 ] || [ $frontend_tokens_exit -ne 0 ] || [ $frontend_test_exit -ne 0 ] || [ $frontend_build_exit -ne 0 ] || [ $frontend_smoke_exit -ne 0 ]; then
            echo -e "${RED}❌ Frontend tests failed${NC}"
            test_exit_code=1
        else
            echo -e "${GREEN}✓ Frontend tests passed${NC}"
        fi
    else
        cd ..
        echo -e "${YELLOW}⚠ No frontend test script found, skipping${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Frontend directory not found, skipping${NC}"
fi

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
