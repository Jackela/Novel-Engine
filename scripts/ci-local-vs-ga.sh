#!/usr/bin/env bash
#
# ci-local-vs-ga.sh - Compare local environment with GitHub Actions CI
#
# This script helps identify differences between local and CI environments
# to catch issues before pushing.
#

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Local vs CI Environment Comparison${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

ISSUES_FOUND=0

# Check Python version
LOCAL_PYTHON=$(python3 --version 2>&1 | head -1)
echo -e "Python Version:"
echo -e "  Local:    $LOCAL_PYTHON"
echo -e "  CI:       Python 3.11.x"
if [[ ! "$LOCAL_PYTHON" =~ "3.11" ]]; then
    echo -e "  ${YELLOW}⚠ Version mismatch - CI uses Python 3.11${NC}"
    ((ISSUES_FOUND++))
else
    echo -e "  ${GREEN}✓ Match${NC}"
fi
echo ""

# Check environment variables
echo -e "Environment Variables:"
echo -e "  ORCHESTRATOR_MODE: ${ORCHESTRATOR_MODE:-not set}"
if [ -z "${ORCHESTRATOR_MODE}" ]; then
    echo -e "  ${YELLOW}⚠ Not set (CI uses 'testing')${NC}"
    echo -e "  ${YELLOW}  Fix: export ORCHESTRATOR_MODE=testing or source .env.ci${NC}"
    ((ISSUES_FOUND++))
else
    echo -e "  ${GREEN}✓ Set to '$ORCHESTRATOR_MODE'${NC}"
fi

echo -e "  PYTHONPATH: ${PYTHONPATH:-not set}"
if [[ ! "$PYTHONPATH" =~ "src" ]]; then
    echo -e "  ${YELLOW}⚠ May not include src directory${NC}"
    echo -e "  ${YELLOW}  Fix: export PYTHONPATH=\$(pwd):\$(pwd)/src or source .env.ci${NC}"
else
    echo -e "  ${GREEN}✓ Includes src directory${NC}"
fi
echo ""

# Check if .env.ci is sourced
echo -e "CI Environment File:"
if [ -f "$PROJECT_ROOT/.env.ci" ]; then
    echo -e "  ${GREEN}✓ .env.ci exists${NC}"
    echo -e "  Run 'source .env.ci' to load CI environment variables"
else
    echo -e "  ${YELLOW}⚠ .env.ci not found${NC}"
    echo -e "  ${YELLOW}  Run the setup script to create it${NC}"
fi
echo ""

# Check git hooks
echo -e "Git Hooks:"
HOOKS_PATH=$(git config --get core.hooksPath 2>/dev/null || echo "not configured")
if [ "$HOOKS_PATH" = ".githooks" ]; then
    echo -e "  ${GREEN}✓ Using .githooks directory${NC}"
else
    echo -e "  ${YELLOW}⚠ Not using .githooks ($HOOKS_PATH)${NC}"
    echo -e "  ${YELLOW}  Run './scripts/setup-hooks.sh' to enable pre-push checks${NC}"
    ((ISSUES_FOUND++))
fi
echo ""

# Summary
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
if [ $ISSUES_FOUND -gt 0 ]; then
    echo -e "${YELLOW}Found $ISSUES_FOUND potential issue(s) that may cause CI to fail locally${NC}"
    echo ""
    echo -e "Quick fixes:"
    echo -e "  1. source .env.ci           # Load CI environment variables"
    echo -e "  2. ./scripts/setup-hooks.sh # Enable pre-push validation"
    echo ""
else
    echo -e "${GREEN}Local environment appears to match CI configuration${NC}"
    echo ""
fi
