#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=UTF-8
VENV="./.venv/bin/python"
[ -x "$VENV" ] || { echo "venv missing"; exit 2; }
# Use -n auto for parallel execution (auto-detect CPU count)
# Remove -n flag if you need serial execution for debugging
exec "$VENV" -m pytest -n auto -q -rA --junitxml=pytest-report.xml --color=no -p asyncio -p timeout "$@"
