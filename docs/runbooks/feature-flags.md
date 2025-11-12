# Runbook: Feature Flags (Semantic Cache)

## Flags
- enable_exact_cache (default: true)
- enable_semantic_cache (default: true)
- enable_single_flight (default: true)

## Rollout
- Canary: turn on exact first, then semantic with conservative thresholds.
- Observe metrics before enabling single-flight under peak load.

## Rollback
- Disable semantic cache and single-flight via flags; exact cache can remain on if stable.

