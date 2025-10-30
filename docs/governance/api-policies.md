# API Rate Limit & Idempotency Policies

## Rate Limit Tiers

| Tier | Applies To | Requests / Minute | Notes |
|------|------------|-------------------|-------|
| User | Authenticated user token | 120 | Burst tolerance of +20 within window. |
| Tenant | All users under tenant | 600 | Reset interval 60 seconds. |
| Anonymous | Unauthenticated traffic | 30 | Health endpoints excluded. |

- Limits enforced via API gateway; headers `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` returned on every response.
- Rate limit breaches return HTTP 429 with problem details including `retry_after`.

## Idempotency

- All POST/PUT/PATCH/DELETE requests that mutate state require `Idempotency-Key`.
- Keys must be unique per tenant/user combination for 24 hours; collisions return stored response.
- Gateway stores request hash (method, path, body) to detect mismatched retries; mismatches return 409 Conflict.

## Client Guidance

1. Generate UUIDv4 as idempotency key.
2. Retry on network timeouts with same key.
3. On 429, backoff per `Retry-After`.

## Compliance Checklist

- [ ] Contract documentation references headers and key requirements.
- [ ] Backend services log idempotency key for troubleshooting (redacted in exports).
- [ ] Monitoring alerts configured when tenant traffic approaches 80% of quota.
