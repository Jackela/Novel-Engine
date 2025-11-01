#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "== Smoke: Health =="
curl -s "$BASE_URL/health" | jq . >/dev/null || curl -s "$BASE_URL/health"

echo "== Smoke: Metrics (before) =="
curl -s "$BASE_URL/cache/metrics" | jq . || true

echo "== Smoke: Invalidate (no-op) =="
curl -s -X POST "$BASE_URL/cache/invalidate" \
  -H 'Content-Type: application/json' \
  -d '{"all_of":["model:test-model"]}' | jq . || true

echo "== Smoke: SSE replay =="
curl -s -X POST "$BASE_URL/cache/chunk/demo" \
  -H 'Content-Type: application/json' \
  -d '{"seq":1,"data":"hello"}' | jq . || true
curl -s -X POST "$BASE_URL/cache/chunk/demo/complete" | jq . || true
echo "-- Stream --"
curl -N "$BASE_URL/cache/stream/demo" || true

echo "== Smoke: Metrics (after) =="
curl -s "$BASE_URL/cache/metrics" | jq . || true

echo "== Smoke: Savings Report (md) =="
python scripts/reporting/cache_savings_report.py --format md --output - || true

echo "Done."

