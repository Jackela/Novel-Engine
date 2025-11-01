# Quickstart: Semantic Cache

## Enable Feature
- Toggle on: exact cache, semantic cache, single-flight, streaming replay
- Set thresholds: High=0.92, Low=0.85; guards keyword≥0.40, length Δ≤15%
- Ensure tag-driven invalidation events are published on template/index/model/character changes

## Integrations
- LLM client: interception order — Exact → Semantic → Provider; write on completion
- Coordinator: enable single-flight merge window and replay store; negative cache & backoff on provider errors
- Tooling: use POST /cache/invalidate with tags to clear impacted entries; GET /cache/metrics for dashboards

## Observability
- Track: hit rates (exact/semantic), similarity distribution, single-flight merges, replays, invalidations, evictions, saved cost/tokens
- Alert on: semantic false-positive suspicions, high miss under high similarity, invalidation backlog

## Rollout Tips
- Start with semantic cache disabled in canary → enable with conservative thresholds → move to balanced after validation
- Pre-warm common prompts via controlled runs to seed cache safely
