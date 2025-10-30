# Regression Benchmark — 2025-10-29

## Test Matrix

| Suite | Command | Result | Duration |
|-------|---------|--------|----------|
| Pytest core | `pytest --cov=src` | PASS | 11m 32s |
| Playwright smoke | `npm run --prefix frontend test:e2e -- --project=chromium` | PASS | 6m 18s |
| k6 API smoke | `k6 run tests/perf/smoke.js` | PASS | 3m 02s |

## Coverage Snapshot

- `src/`: 20.45% (matches CI baseline)
- Key gaps: persona fallback logic, campaign repository mutations

## Observations

- Contract endpoints currently emit incomplete rate-limit headers; documentation update will address expectations before implementation changes.
- k6 smoke test produced minor p95 latency increase when cache cold; capture in observability baseline for follow-up.
