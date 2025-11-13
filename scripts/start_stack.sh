#!/usr/bin/env bash
set -Eeuo pipefail

# Convenience wrapper for starting the local Novel Engine stack without blocking
# the current terminal session. Internally proxies to scripts/run_stack.sh.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/run_stack.sh" start "$@"
