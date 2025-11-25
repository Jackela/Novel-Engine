#!/bin/bash
#
# Test Pyramid Quick Check
# =========================
#
# Quick wrapper script for test pyramid monitoring
#
# Usage:
#   ./check-pyramid.sh              # Console report
#   ./check-pyramid.sh --json       # JSON output
#   ./check-pyramid.sh --html       # HTML report
#   ./check-pyramid.sh --save       # Save history
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
FORMAT="console"
SAVE_HISTORY=""
OUTPUT_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --json)
            FORMAT="json"
            shift
            ;;
        --html)
            FORMAT="html"
            shift
            ;;
        --markdown|--md)
            FORMAT="markdown"
            shift
            ;;
        --save|--history)
            SAVE_HISTORY="--save-history"
            shift
            ;;
        --output|-o)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --json         Output JSON format"
            echo "  --html         Output HTML format"
            echo "  --markdown     Output Markdown format"
            echo "  --save         Save historical data"
            echo "  --output FILE  Write to file instead of stdout"
            echo "  --help         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Change to project root
cd "$PROJECT_ROOT"

# Build command
CMD="python scripts/testing/test-pyramid-monitor-fast.py"

if [ -n "$FORMAT" ]; then
    CMD="$CMD --format $FORMAT"
fi

if [ -n "$SAVE_HISTORY" ]; then
    CMD="$CMD $SAVE_HISTORY"
fi

if [ -n "$OUTPUT_FILE" ]; then
    CMD="$CMD --output $OUTPUT_FILE"
fi

# Run the monitor
echo -e "${BLUE}Running Test Pyramid Monitor...${NC}" >&2
echo "" >&2

eval $CMD
EXIT_CODE=$?

echo "" >&2

# Provide feedback based on exit code
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Test pyramid looks good!${NC}" >&2
else
    echo -e "${YELLOW}⚠ Test pyramid needs attention (score < 5.0)${NC}" >&2
fi

# Show history location if saved
if [ -n "$SAVE_HISTORY" ]; then
    echo -e "${BLUE}History saved to .pyramid-history/${NC}" >&2
fi

exit $EXIT_CODE
