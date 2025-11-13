#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/frontend-regression.log"

mkdir -p "$LOG_DIR"
: > "$LOG_FILE"

log_step() {
  local msg="$1"
  printf '\n[%s] %s\n' "$(date +'%Y-%m-%d %H:%M:%S')" "$msg" | tee -a "$LOG_FILE"
}

run_step() {
  local name="$1"
  shift
  log_step "Starting ${name}..."
  (
    cd "$FRONTEND_DIR"
    "$@"
  ) 2>&1 | tee -a "$LOG_FILE"
  log_step "Completed ${name}."
}

log_step "Novel Engine Frontend Regression (lint, type-check, vitest, playwright)"

run_step "ESLint" npm run lint
run_step "Type Check" npm run type-check
run_step "Vitest Suite" env VITEST_MAX_THREADS="${VITEST_MAX_THREADS:-2}" npx vitest run
PLAYWRIGHT_PROJECT="${PLAYWRIGHT_PROJECT:-chromium-desktop}"
run_step "Playwright E2E" env CI=1 npm run test:e2e -- --project="$PLAYWRIGHT_PROJECT"

log_step "All frontend regression steps finished."
