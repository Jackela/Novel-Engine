#!/bin/bash
# Run tests filtered by speed category
# Usage: ./run-by-speed.sh [fast|medium|slow|not-slow]

set -e

CATEGORY="${1:-fast}"

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Running tests by speed: ${CATEGORY}${NC}"
echo "========================================"

case "$CATEGORY" in
    fast)
        echo -e "${GREEN}Running FAST tests (< 100ms)${NC}"
        python -m pytest -m "fast" tests/ -v --tb=short --no-cov
        ;;
    medium)
        echo -e "${YELLOW}Running MEDIUM tests (100ms - 1s)${NC}"
        python -m pytest -m "medium" tests/ -v --tb=short --no-cov
        ;;
    slow)
        echo -e "${RED}Running SLOW tests (> 1s)${NC}"
        python -m pytest -m "slow" tests/ -v --tb=short --no-cov
        ;;
    not-slow)
        echo -e "${GREEN}Running all tests EXCEPT slow tests${NC}"
        python -m pytest -m "not slow" tests/ -v --tb=short --no-cov
        ;;
    all-fast-medium)
        echo -e "${GREEN}Running FAST and MEDIUM tests${NC}"
        python -m pytest -m "fast or medium" tests/ -v --tb=short --no-cov
        ;;
    *)
        echo -e "${RED}Invalid category: $CATEGORY${NC}"
        echo "Usage: $0 [fast|medium|slow|not-slow|all-fast-medium]"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}Test run complete!${NC}"
