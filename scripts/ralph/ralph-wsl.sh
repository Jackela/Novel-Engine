#!/bin/bash
# Ralph for WSL - Windows-friendly version
# Uses WSL bash to run Ralph with proper timeout and signal handling

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRD_FILE="$SCRIPT_DIR/prd.json"
PROGRESS_FILE="$SCRIPT_DIR/progress.txt"

# Windows Claude path (adjust if different)
CLAUDE_CMD="/mnt/c/Users/k7407/.local/bin/claude.exe"

# Parse arguments
TOOL="claude"
MAX_ITERATIONS=10

while [[ $# -gt 0 ]]; do
  case $1 in
    --tool)
      TOOL="$2"
      shift 2
      ;;
    --tool=*)
      TOOL="${1#*=}"
      shift
      ;;
    [0-9]*)
      MAX_ITERATIONS="$1"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

echo "Starting Ralph (WSL) - Tool: $TOOL - Max iterations: $MAX_ITERATIONS"
echo "Claude: $CLAUDE_CMD"
echo ""

for i in $(seq 1 $MAX_ITERATIONS); do
  echo ""
  echo "==============================================================="
  echo "  Ralph Iteration $i of $MAX_ITERATIONS ($TOOL)"
  echo "==============================================================="

  # Run Claude with timeout
  # Use --continue for subsequent iterations
  if [[ $i -eq 1 ]]; then
    # First iteration - fresh start with CLAUDE.md
    OUTPUT=$(timeout 600s "$CLAUDE_CMD" --dangerously-skip-permissions --print < "$SCRIPT_DIR/CLAUDE.md" 2>&1 || echo "[TIMEOUT]")
  else
    # Subsequent iterations - continue previous session
    OUTPUT=$(timeout 600s "$CLAUDE_CMD" --dangerously-skip-permissions -c --print 2>&1 || echo "[TIMEOUT]")
  fi

  # Check for completion signal
  if echo "$OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
    echo ""
    echo "Ralph completed all tasks!"
    echo "Completed at iteration $i of $MAX_ITERATIONS"
    exit 0
  fi

  # Check for timeout
  if echo "$OUTPUT" | grep -q "\[TIMEOUT\]"; then
    echo "⚠️  Iteration timed out, continuing to next..."
  fi

  echo "Iteration $i complete. Continuing..."
  sleep 2
done

echo ""
echo "Ralph reached max iterations ($MAX_ITERATIONS) without completing all tasks."
echo "Check $PROGRESS_FILE for status."
exit 1
