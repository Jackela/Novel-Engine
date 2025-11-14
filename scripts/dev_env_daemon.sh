#!/usr/bin/env bash
# Convenience shim: start the unified dev environment in detached mode.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/dev_env.sh" start --detach "$@"
