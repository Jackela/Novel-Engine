#!/usr/bin/env bash
# Local CI Test Runner
# Mimics GitHub Actions CI workflow without Docker/network requirements

set -e  # Exit on error

echo "================================"
echo "Novel Engine - Local CI Tests"
echo "================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "Step 1: Environment Check"
echo "-------------------------"
python --version
pip --version
echo ""

echo "Step 2: Installing Dependencies"
echo "-------------------------------"
if [ -f "requirements.txt" ]; then
    pip install -q -r requirements.txt
fi
if [ -f "requirements-test.txt" ]; then
    pip install -q -r requirements-test.txt
fi
echo "✓ Dependencies installed"
echo ""

echo "Step 3: Running Smoke Tests (CI)"
echo "--------------------------------"
python -m pytest -q tests/test_enhanced_bridge.py tests/test_character_system_comprehensive.py --junitxml=pytest-report.xml

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ CI smoke tests PASSED${NC}"
else
    echo -e "${RED}✗ CI smoke tests FAILED${NC}"
    exit 1
fi
echo ""

echo "Step 4: Running Unit Tests"
echo "-------------------------"
python -m pytest -q tests/unit/test_character_factory.py tests/unit/test_director_agent_comprehensive.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Critical unit tests PASSED${NC}"
else
    echo -e "${RED}✗ Critical unit tests FAILED${NC}"
    exit 1
fi
echo ""

echo "Step 5: Running Security Tests"
echo "------------------------------"
python -m pytest -q tests/security/

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Security tests PASSED${NC}"
else
    echo -e "${RED}✗ Security tests FAILED${NC}"
    exit 1
fi
echo ""

echo "================================"
echo -e "${GREEN}ALL CI TESTS PASSED ✓${NC}"
echo "================================"
