# Change: Harden API observability and retries

## Why
- Client error handling is inconsistent: correlation IDs, retry hints, and validation details are not standardized, making debugging and telemetry difficult.
- Cross-service retries/backoff need policy so flaky upstreams do not surface as fatal UX errors.

## What Changes
- Define a standard error envelope (correlation id, machine code, human message, retryable hint, validation fields) for 4xx/5xx responses.
- Require client requests to stamp tracing metadata and record latency/attempts for observability.
- Establish retry/backoff policy per endpoint class (idempotent vs. mutation) with caps surfaced to callers.

## Impact
- Affected specs: `api-surface`
- Affected code: shared HTTP client, ApiError normalization, telemetry/logging, retry policies.
