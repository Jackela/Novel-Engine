#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/tmp/dev_env"
LOG_FILE="$ROOT_DIR/tmp/dev_env.log"
BACKEND_PID_FILE="$RUNTIME_DIR/backend.pid"
FRONTEND_PID_FILE="$RUNTIME_DIR/frontend.pid"

stop_pid() {
  local label=$1
  local pid_file=$2
  if [[ ! -f "$pid_file" ]]; then
    echo "[dev-env] No $label PID file found ($pid_file)"
    return
  fi
  local pid
  pid=$(<"$pid_file")
  if [[ -z "$pid" ]]; then
    echo "[dev-env] Empty PID file for $label; removing"
    rm -f "$pid_file"
    return
  fi
  if kill -0 "$pid" >/dev/null 2>&1; then
    echo "[dev-env] Stopping $label (PID $pid)"
    kill "$pid" >/dev/null 2>&1 || true
    wait "$pid" >/dev/null 2>&1 || true
  else
    echo "[dev-env] $label process $pid not running"
  fi
  rm -f "$pid_file"
}

stop_pid "backend" "$BACKEND_PID_FILE"
stop_pid "frontend" "$FRONTEND_PID_FILE"

echo "[dev-env] Remaining background processes (if any) are logged in $LOG_FILE"
