#!/bin/bash
# Run E2E tests for Novel Engine
# Usage: ./scripts/run_e2e_tests.sh [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Novel Engine E2E Test Runner${NC}"
echo "================================"

# Parse arguments
VERBOSE=""
MARKERS="e2e"
REPORT_DIR="reports/test-results"

while [[ $# -gt 0 ]]; do
  case $1 in
    -v|--verbose)
      VERBOSE="-vv"
      shift
      ;;
    -m|--markers)
      MARKERS="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [options]"
      echo ""
      echo "Options:"
      echo "  -v, --verbose     Verbose output"
      echo "  -m, --markers     Pytest markers (default: e2e)"
      echo "  -h, --help        Show this help"
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      exit 1
      ;;
  esac
done

# Setup environment
echo -e "${YELLOW}Setting up test environment...${NC}"
export DEBUG="true"
export ENABLE_RATE_LIMITING="false"
export ENABLE_AUTH="false"
export DATABASE_PATH="data/test_e2e.db"

# Create required directories
mkdir -p data
mkdir -p logs
mkdir -p "$REPORT_DIR"

# Clean old test database
if [ -f "$DATABASE_PATH" ]; then
  echo "Removing old test database..."
  rm -f "$DATABASE_PATH"
fi

# Run tests
echo -e "${YELLOW}Running E2E tests...${NC}"
pytest tests/e2e/ \
  $VERBOSE \
  -m "$MARKERS" \
  --tb=short \
  --durations=10 \
  --junitxml="$REPORT_DIR/e2e-results.xml" \
  || TEST_EXIT_CODE=$?

# Report results
if [ ${TEST_EXIT_CODE:-0} -eq 0 ]; then
  echo -e "${GREEN}All E2E tests passed!${NC}"
else
  echo -e "${RED}Some E2E tests failed (exit code: ${TEST_EXIT_CODE})${NC}"
  echo -e "${YELLOW}Check $REPORT_DIR/e2e-results.xml for details${NC}"
fi

# Cleanup
echo "Cleaning up test database..."
rm -f "$DATABASE_PATH"

exit ${TEST_EXIT_CODE:-0}
