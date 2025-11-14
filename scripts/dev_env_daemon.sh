#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/tmp"
RUNTIME_DIR="$LOG_DIR/dev_env"
LOG_FILE="$LOG_DIR/dev_env.log"
BACKEND_PID_FILE="$RUNTIME_DIR/backend.pid"
FRONTEND_PID_FILE="$RUNTIME_DIR/frontend.pid"
BACKEND_PORT="${API_PORT:-${NOVEL_ENGINE_API_PORT:-8000}}"
BACKEND_HOST="${API_HOST:-127.0.0.1}"
FRONTEND_PORT="${VITE_PORT:-${NOVEL_ENGINE_VITE_PORT:-3000}}"
FRONTEND_HOST="${VITE_HOST:-127.0.0.1}"
STARTUP_TIMEOUT="${DEV_ENV_TIMEOUT:-90}"
POLL_INTERVAL=2
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python)"
fi

if [[ -z "${PYTHONPATH:-}" ]]; then
  export PYTHONPATH="$ROOT_DIR"
else
  export PYTHONPATH="$ROOT_DIR:$PYTHONPATH"
fi

mkdir -p "$LOG_DIR" "$RUNTIME_DIR"
touch "$LOG_FILE"

info() { printf "[dev-env] %s\n" "$*"; }

require_cmd() {
  local cmd=$1
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Required command '$cmd' not found in PATH" >&2
    exit 1
  fi
}

kill_if_stale() {
  local pid_file=$1
  if [[ -f "$pid_file" ]]; then
    local pid
    pid=$(<"$pid_file")
    if [[ -n "$pid" && -e /proc/$pid ]]; then
      info "Existing dev env process ($pid) still running; skipping restart. Use scripts/stop_dev_env.sh if you want a clean slate."
      return 1
    fi
    rm -f "$pid_file"
  fi
  return 0
}

start_backend() {
  if ! kill_if_stale "$BACKEND_PID_FILE"; then
    return
  fi
  info "Starting backend API on $BACKEND_HOST:$BACKEND_PORT (python: $PYTHON_BIN)"
  local api_debug="${API_DEBUG:-0}"
  (
    cd "$ROOT_DIR"
    API_PORT="$BACKEND_PORT" API_HOST="$BACKEND_HOST" API_DEBUG="$api_debug" "$PYTHON_BIN" api_server.py
  ) >>"$LOG_FILE" 2>&1 &
  local pid=$!
  echo "$pid" > "$BACKEND_PID_FILE"
  info "Backend PID: $pid (logs → $LOG_FILE)"
}

start_frontend() {
  if ! kill_if_stale "$FRONTEND_PID_FILE"; then
    return
  fi
  info "Starting frontend Vite dev server on $FRONTEND_HOST:$FRONTEND_PORT"
  (
    cd "$ROOT_DIR/frontend"
    VITE_PORT="$FRONTEND_PORT" VITE_HOST="$FRONTEND_HOST" npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT"
  ) >>"$LOG_FILE" 2>&1 &
  local pid=$!
  echo "$pid" > "$FRONTEND_PID_FILE"
  info "Frontend PID: $pid (logs → $LOG_FILE)"
}

wait_for_endpoint() {
  local name=$1
  local url=$2
  local deadline=$(( $(date +%s) + STARTUP_TIMEOUT ))

  until [[ $(date +%s) -ge $deadline ]]; do
    if curl --silent --show-error --max-time 2 "$url" >/dev/null 2>&1; then
      info "$name ready at $url"
      return 0
    fi
    sleep "$POLL_INTERVAL"
  done
  echo "Timed out waiting for $name at $url" >&2
  return 1
}

main() {
  if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Python interpreter '$PYTHON_BIN' not found or executable" >&2
    exit 1
  fi
  require_cmd npm
  require_cmd curl

  start_backend || true
  start_frontend || true

  local backend_url="http://$BACKEND_HOST:$BACKEND_PORT/health"
  local frontend_url="http://$FRONTEND_HOST:$FRONTEND_PORT/"

  local backend_ready=0
  local frontend_ready=0

  if wait_for_endpoint "Backend" "$backend_url"; then
    backend_ready=1
  fi
  if wait_for_endpoint "Frontend" "$frontend_url"; then
    frontend_ready=1
  fi

  if [[ $backend_ready -eq 1 && $frontend_ready -eq 1 ]]; then
    info "All services ready. Access frontend at $frontend_url"
    info "Use scripts/stop_dev_env.sh to stop background processes."
    exit 0
  fi

  echo "One or more services failed to start. Check $LOG_FILE for details." >&2
  exit 1
}

main "$@"
