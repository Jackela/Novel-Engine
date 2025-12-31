## 1. Implementation
- [x] 1.1 Implement standard error envelope parsing/serialization (correlation id, code, message, retryable, validation fields).
- [x] 1.2 Add client-side tracing metadata + latency/attempt logging on all HTTP calls.
- [x] 1.3 Define retry/backoff profiles per endpoint class (idempotent GET vs. mutations) and enforce caps.
- [x] 1.4 Wire ApiError normalization to expose retry hints and validation details consistently.

## 2. Validation
- [x] 2.1 `npm run lint:all`
- [x] 2.2 `npm run type-check`
- [x] 2.3 `npm run test`
- [x] 2.4 `npm run test:e2e:smoke`
