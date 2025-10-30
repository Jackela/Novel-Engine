# Resiliency Controls

## Timeouts & Retries

- **Gemini ACL**: 10s total timeout with exponential backoff (250ms → 2s) for 3 attempts.
- **Internal HTTP calls**: 5s timeout, single retry on idempotent verbs.
- **Database operations**: 3s timeout; no retries on mutations (fail fast).

## Circuit Breakers

- Gemini ACL triggers open state after 5 consecutive failures; fallback persona heuristic engaged.
- Event bus consumer circuit opens if processing lag > 60s.

## Bulkheads

- Persona intelligence executor pool isolated from narrative rendering to prevent cascading failures.
- Background job queue has per-context concurrency limits.

## Degradation Strategies

- If narrative rendering fails, store simplified log and mark event for reprocessing.
- If feature flag service unreachable, default to last known value stored in Redis (TTL 5 minutes).

## Testing

- Chaos drills run quarterly; scripts located under `tests/resiliency/`.
- Incident response runbook ties alerts to rollback or kill-switch actions.
