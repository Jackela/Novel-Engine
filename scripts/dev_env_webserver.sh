#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$ROOT_DIR/tmp/dev_env.log"
STOP_SCRIPT="$ROOT_DIR/scripts/stop_dev_env.sh"
START_SCRIPT="$ROOT_DIR/scripts/dev_env_daemon.sh"
TAIL_PID=""

cleanup() {
  if [[ -n "$TAIL_PID" ]]; then
    kill "$TAIL_PID" >/dev/null 2>&1 || true
  fi
  if [[ -x "$STOP_SCRIPT" ]]; then
    bash "$STOP_SCRIPT" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

bash "$START_SCRIPT"

tail -F "$LOG_FILE" &
TAIL_PID=$!
wait "$TAIL_PID"
