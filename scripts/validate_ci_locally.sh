#!/usr/bin/env bash
# CI/CD Local Validation Script
# Purpose: Run exact same tests and coverage checks as GitHub Actions Quality Assurance Pipeline
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

# Check Python version (must be 3.11)
echo "📋 Checking Python version..."
python_version=$(python --version 2>&1 | awk '{print $2}')
if [[ ! "$python_version" =~ ^3\.11 ]]; then
    echo -e "${RED}❌ Python 3.11 required for local validation${NC}"
    echo -e "   ${YELLOW}Found: Python $python_version${NC}"
    echo -e "   ${YELLOW}Install: https://www.python.org/downloads/${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $python_version detected${NC}"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install pytest pytest-cov coverage httpx pytest-timeout pytest-asyncio --quiet
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Run exact CI commands (matching GitHub Actions quality_assurance.yml test-suite job)
echo "🧪 Running tests with coverage (this matches GitHub Actions exactly)..."
echo ""

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

# Capture exit code
test_exit_code=$?

echo ""
echo "=========================================="
if [ $test_exit_code -eq 0 ]; then
    echo -e "${GREEN}✅ Validation PASSED${NC}"
    echo -e "${GREEN}   All tests passed and coverage meets 30% threshold${NC}"
    echo -e "${GREEN}   Safe to push to GitHub${NC}"
else
    echo -e "${RED}❌ Validation FAILED${NC}"
    echo -e "${RED}   Fix issues before pushing to GitHub${NC}"
    echo ""
    echo "Common issues:"
    echo "  - Test failures: Check test output above for failing tests"
    echo "  - Coverage below 30%: Add tests or check .coveragerc configuration"
    echo "  - Import errors: Verify PYTHONPATH includes src/"
fi
echo "=========================================="

exit $test_exit_code
