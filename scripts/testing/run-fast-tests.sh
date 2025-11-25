#!/bin/bash
# Run only fast tests for quick feedback
# Fast tests are defined as tests that complete in < 100ms

set -e

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Running Fast Tests (< 100ms)${NC}"
echo "================================"
echo ""

# Run fast unit tests
echo -e "${GREEN}Fast Unit Tests:${NC}"
python -m pytest -m "unit and fast" tests/unit/ -q --tb=short --no-cov

echo ""
echo -e "${GREEN}Fast Integration Tests:${NC}"
python -m pytest -m "integration and fast" tests/integration/ -q --tb=short --no-cov

echo ""
echo -e "${BLUE}Fast test run complete!${NC}"
