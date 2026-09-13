#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for Novel Engine.
# Ensures Node.js 24 + pnpm 11, installs the workspace, and builds the SPA and
# TS server so `cli serve` can serve the Studio and JSON API from one process.
set -euo pipefail

cd "$(dirname "$0")/.."

export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
# shellcheck disable=SC1091
. "$NVM_DIR/nvm.sh"

# Server engines require Node >= 24 (matches .github/workflows/ci.yml).
if ! nvm which 24 >/dev/null 2>&1; then
  nvm install 24
fi
nvm alias default 24 >/dev/null
nvm use 24 >/dev/null

# Pin the workspace package manager (package.json: pnpm@11.6.0).
corepack enable
corepack prepare pnpm@11.6.0 --activate

node --version
pnpm --version

# better-sqlite3 compiles from source via node-gyp; the base image ships
# python3/make/g++. Frozen install keeps the committed lockfile authoritative.
pnpm install --frozen-lockfile

# Build the production runtime artifacts: the studio SPA (frontend/dist) and the
# TS server (server/dist). `cli serve` serves both from a single Node process.
pnpm --dir frontend build
pnpm --dir server build
