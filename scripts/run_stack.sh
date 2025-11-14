#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/tmp/dev_env"
LOG_FILE="$ROOT_DIR/tmp/dev_env.log"
START_SCRIPT="$ROOT_DIR/scripts/dev_env_daemon.sh"
STOP_SCRIPT="$ROOT_DIR/scripts/stop_dev_env.sh"

usage() {
  cat <<'USAGE'
Usage: scripts/run_stack.sh [start|stop|status|logs]

Commands:
  start   Launch backend (api_server.py) and frontend (npm run dev) in the background.
  stop    Terminate any stack processes started via this helper.
  status  Report whether backend/frontend PIDs are running.
  logs    Tail the shared dev_env log file.
USAGE
}

status() {
  local backend_pid_file="$RUNTIME_DIR/backend.pid"
  local frontend_pid_file="$RUNTIME_DIR/frontend.pid"

  if [[ -f "$backend_pid_file" ]]; then
    local backend_pid
    backend_pid=$(<"$backend_pid_file")
    if [[ -n "$backend_pid" && -e /proc/$backend_pid ]]; then
      echo "Backend: running (pid $backend_pid)"
    else
      echo "Backend: not running"
    fi
  else
    echo "Backend: not running"
  fi

  if [[ -f "$frontend_pid_file" ]]; then
    local frontend_pid
    frontend_pid=$(<"$frontend_pid_file")
    if [[ -n "$frontend_pid" && -e /proc/$frontend_pid ]]; then
      echo "Frontend: running (pid $frontend_pid)"
    else
      echo "Frontend: not running"
    fi
  else
    echo "Frontend: not running"
  fi
}

command="${1:-start}"
case "$command" in
  start)
    "$START_SCRIPT"
    ;;
  stop)
    "$STOP_SCRIPT"
    ;;
  status)
    status
    ;;
  logs)
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"
    tail -f "$LOG_FILE"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    echo "Unknown command: $command" >&2
    usage
    exit 1
    ;;
esac
