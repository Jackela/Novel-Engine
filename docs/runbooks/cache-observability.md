# Runbook: Cache Observability

## Metrics Endpoints
- GET `/cache/metrics`: JSON snapshot of hits, size, invalidations, single-flight merges, replays, saved_tokens, saved_cost.

## Logs
- Ensure cache hit/miss, semantic similarity, and invalidation events are logged at INFO with request correlation IDs.

## Dashboards
- Start with the metrics endpoint; if/when Prometheus is adopted, export counters with the same names.

## Alerts
- High semantic false-positive suspicion: spike in low-similarity hits.
- Invalidation backlog: increasing cache size after frequent index/template changes.

