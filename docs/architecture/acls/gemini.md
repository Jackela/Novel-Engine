# Gemini Anti-Corruption Layer

## Responsibilities

1. **Tenant Isolation** — attach `tenant_id` to every outbound request header and
   segregate cache keys using `tenant:{tenant_id}:persona:{persona_id}:turn`.
2. **Caching** — cache persona prompt responses for 900 seconds (Redis TTL) to
   reduce Gemini quota usage; invalidate on persona profile updates.
3. **Retries & Backoff** — perform up to 3 retries with exponential backoff
   (initial 250ms, max 2s). Abort on HTTP 4xx except 429 (rate limit).
4. **Fallback Strategy** — switch to local decision heuristic when Gemini returns
   non-retryable errors after retries; log fallback events with `machine_spirit`
   tag for monitoring.
5. **Observability** — emit OpenTelemetry spans `persona.gemini.request` with
   attributes for `persona_id`, `tenant_id`, `cache_hit`, and `fallback_used`.
6. **Security** — read API key from Vault/KMS; never write to logs. Enforce TLS
   1.2+; verify certificate pinning per provider guidance.

## Sequence Overview

1. Persona agent forms request payload (persona traits, campaign context).
2. ACL enriches with tenant metadata and correlation IDs.
3. Redis cache checked; if hit, return cached response and record metric.
4. Execute Gemini call with retries/backoff.
5. On success, persist response to cache; on failure, trigger fallback logic.
6. Publish outcome to event bus for audit trail.

## Future Enhancements

- Support configurable cache TTL per persona persona sensitivity.
- Evaluate circuit breaker integration if Gemini experiences sustained outages.
