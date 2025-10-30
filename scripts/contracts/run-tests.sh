#!/usr/bin/env bash
#
# StoryForge Contract Test Runner
# Usage: scripts/contracts/run-tests.sh [spec-path]

set -euo pipefail

DEFAULT_SPEC="specs/001-best-practice-refactor/contracts/openapi-refactor.yaml"
SPEC_PATH="${1:-$DEFAULT_SPEC}"

if [[ ! -f "$SPEC_PATH" ]]; then
  echo "error: OpenAPI spec not found at '$SPEC_PATH'" >&2
  exit 2
fi

if ! command -v npx >/dev/null 2>&1; then
  echo "error: npx is required to run the contract linting workflow." >&2
  echo "Install Node.js (>=18) and ensure npx is on PATH." >&2
  exit 127
fi

echo "Linting API contract: $SPEC_PATH"
npx --yes @redocly/openapi-cli@1.26.0 lint "$SPEC_PATH"
