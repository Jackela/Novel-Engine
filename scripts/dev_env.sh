#!/usr/bin/env bash
#
# Unified dev-environment helper for Novel-Engine.
# - Starts FastAPI (uvicorn) + Vite dev server with one command
# - Provides stop/status/logs utilities
# - Supports detached/daemon mode for CI or Playwright harnesses

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${REPO_ROOT}/tmp/dev_env"
mkdir -p "${LOG_DIR}"

BACKEND_LOG="${LOG_DIR}/backend.log"
FRONTEND_LOG="${LOG_DIR}/frontend.log"
BACKEND_PID_FILE="${LOG_DIR}/backend.pid"
FRONTEND_PID_FILE="${LOG_DIR}/frontend.pid"

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
API_RELOAD="${API_RELOAD:-true}"
VITE_HOST="${VITE_HOST:-127.0.0.1}"
VITE_PORT="${VITE_PORT:-3000}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
NODE_ENV="${NODE_ENV:-development}"

TAIL_PIDS=()

usage() {
  cat <<'EOF'
Usage: scripts/dev_env.sh <command> [options]

Commands:
  start [--detach] [--no-backend] [--no-frontend]   Start FastAPI + Vite (default).
  stop                                              Stop any running dev services.
  status                                            Show process status for both services.
  logs                                              Tail both logs with prefixes.
  restart                                           Stop (if needed) then start again.
  help                                              Show this message.

Environment:
  API_HOST / API_PORT       Override FastAPI bind host/port (default 127.0.0.1:8000).
  API_RELOAD                Set to "false" to disable uvicorn reload (default true).
  VITE_HOST / VITE_PORT     Override Vite bind host/port (default 127.0.0.1:3000).
  PYTHON_BIN                Python executable to run uvicorn (default python3).

Examples:
  scripts/dev_env.sh start
  scripts/dev_env.sh start --detach
  scripts/dev_env.sh stop
  scripts/dev_env.sh logs
EOF
}

color() {
  local code="$1"; shift
  printf "\033[%sm%s\033[0m" "${code}" "$*"
}

is_pid_running() {
  local pid_file="$1"
  [[ -f "${pid_file}" ]] || return 1
  local pid
  pid="$(cat "${pid_file}")"
  if ps -p "${pid}" >/dev/null 2>&1; then
    return 0
  fi
  rm -f "${pid_file}"
  return 1
}

ensure_tools() {
  command -v "${PYTHON_BIN}" >/dev/null 2>&1 || {
    echo "❌ Missing python executable '${PYTHON_BIN}'. Set PYTHON_BIN or install Python 3.11+."
    exit 1
  }
  if (( RUN_FRONTEND )); then
    command -v npm >/dev/null 2>&1 || {
      echo "❌ npm is required to run the frontend dev server."
      exit 1
    }
  fi
}

ensure_frontend_deps() {
  [[ ${RUN_FRONTEND} -eq 1 ]] || return 0
  if [[ ! -d "${REPO_ROOT}/frontend/node_modules" ]]; then
    echo "📦 Installing frontend dependencies (npm install)..."
    (cd "${REPO_ROOT}/frontend" && npm install --no-audit --no-fund >/dev/null)
  fi
}

start_backend() {
  if ! (( RUN_BACKEND )); then
    return 0
  fi
  if is_pid_running "${BACKEND_PID_FILE}"; then
    echo "ℹ️  Backend already running (pid $(cat "${BACKEND_PID_FILE}"))."
    return 0
  fi

  echo "▶️  Starting FastAPI server on ${API_HOST}:${API_PORT}..."
  local reload_flag=()
  [[ "${API_RELOAD,,}" == "false" ]] || reload_flag+=(--reload)

  (
    cd "${REPO_ROOT}"
    exec "${PYTHON_BIN}" -m uvicorn src.api.main_api_server:app \
      --host "${API_HOST}" \
      --port "${API_PORT}" \
      "${reload_flag[@]}"
  ) >>"${BACKEND_LOG}" 2>&1 &
  echo $! > "${BACKEND_PID_FILE}"
  sleep 0.3
}

start_frontend() {
  if ! (( RUN_FRONTEND )); then
    return 0
  fi
  if is_pid_running "${FRONTEND_PID_FILE}"; then
    echo "ℹ️  Frontend already running (pid $(cat "${FRONTEND_PID_FILE}"))."
    return 0
  fi
  ensure_frontend_deps
  echo "▶️  Starting Vite dev server on ${VITE_HOST}:${VITE_PORT}..."
  (
    cd "${REPO_ROOT}/frontend"
    exec npm run dev -- --host "${VITE_HOST}" --port "${VITE_PORT}"
  ) >>"${FRONTEND_LOG}" 2>&1 &
  echo $! > "${FRONTEND_PID_FILE}"
  sleep 0.3
}

stop_process() {
  local label="$1"
  local pid_file="$2"
  if ! is_pid_running "${pid_file}"; then
    return 0
  fi
  local pid
  pid="$(cat "${pid_file}")"
  echo "⏹  Stopping ${label} (pid ${pid})..."
  kill "${pid}" >/dev/null 2>&1 || true
  wait "${pid}" 2>/dev/null || true
  rm -f "${pid_file}"
}

stop_all() {
  stop_process "FastAPI" "${BACKEND_PID_FILE}"
  stop_process "Vite dev server" "${FRONTEND_PID_FILE}"
}

stream_log() {
  local label="$1" file="$2"
  [[ -f "${file}" ]] || touch "${file}"
  stdbuf -oL tail -n0 -F "${file}" | sed -u "s/^/[$label] /" &
  TAIL_PIDS+=($!)
}

attach_logs() {
  [[ ${DETACH} -eq 1 ]] && return 0
  echo "📡 Streaming logs (Ctrl+C to stop)..."
  trap cleanup INT TERM
  stream_log "backend" "${BACKEND_LOG}"
  stream_log "frontend" "${FRONTEND_LOG}"
  wait
}

cleanup() {
  trap - INT TERM
  stop_all
  for pid in "${TAIL_PIDS[@]:-}"; do
    kill "${pid}" >/dev/null 2>&1 || true
  done
  exit 0
}

status() {
  if is_pid_running "${BACKEND_PID_FILE}"; then
    echo "$(color 32 '✔') FastAPI running (pid $(cat "${BACKEND_PID_FILE}"))"
  else
    echo "$(color 31 '✖') FastAPI stopped"
  fi
  if is_pid_running "${FRONTEND_PID_FILE}"; then
    echo "$(color 32 '✔') Frontend dev server running (pid $(cat "${FRONTEND_PID_FILE}"))"
  else
    echo "$(color 31 '✖') Frontend dev server stopped"
  fi
}

tail_logs() {
  echo "📑 Tail logs (Ctrl+C to exit)..."
  stream_log "backend" "${BACKEND_LOG}"
  stream_log "frontend" "${FRONTEND_LOG}"
  trap 'for pid in "${TAIL_PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done' INT TERM
  wait
}

COMMAND="${1:-help}"
shift || true

RUN_BACKEND=1
RUN_FRONTEND=1
DETACH=0

case "${COMMAND}" in
  start)
    while [[ $# -gt 0 ]]; do
      case "$1" in
        -d|--detach) DETACH=1 ;;
        --no-backend) RUN_BACKEND=0 ;;
        --no-frontend) RUN_FRONTEND=0 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option '$1'"; usage; exit 1 ;;
      esac
      shift
    done
    if (( ! RUN_BACKEND && ! RUN_FRONTEND )); then
      echo "Nothing to start (both services disabled)." >&2
      exit 1
    fi
    ensure_tools
    start_backend
    start_frontend
    if (( DETACH )); then
      echo "✅ Dev environment running in background."
      status
      exit 0
    fi
    attach_logs
    ;;
  stop)
    stop_all
    echo "✅ Dev environment stopped."
    ;;
  status)
    status
    ;;
  logs)
    tail_logs
    ;;
  restart)
    stop_all
    "$0" start "$@"
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    echo "Unknown command '${COMMAND}'"
    usage
    exit 1
    ;;
esac
