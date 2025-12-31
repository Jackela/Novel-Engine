## ADDED Requirements
### Requirement: Standard error envelope with retry hint and correlation id
API responses for 4xx/5xx MUST return a JSON envelope containing `code`, `message`, `retryable` (boolean), `correlation_id`, and optional `fields` (validation issues) so clients can surface actionable errors and link to logs.

#### Scenario: Server error returns traceable envelope
- **WHEN** a client calls `GET /api/characters` and the server returns 500
- **THEN** the response body includes `code` (e.g., `HTTP_500`), `message`, `retryable=true`, and a non-empty `correlation_id`
- **AND** clients log/emit the correlation id alongside the HTTP status for debugging.

#### Scenario: Validation error returns field details
- **WHEN** a client POSTs invalid data
- **THEN** the 422 response includes `fields` entries with `path` and `message` per invalid field and `retryable=false`.

### Requirement: Client requests carry observability metadata
First-party clients MUST attach tracing headers (e.g., `X-Request-Id`, `X-Client`, `X-Request-Duration`) and record attempt counts/latency per request for downstream logging/metrics.

#### Scenario: Idempotent request emits tracing headers
- **WHEN** the frontend issues `GET /api/characters`
- **THEN** the request includes a unique `X-Request-Id`, client identifier, and the client records latency/attempt count for the call
- **AND** retries reuse the same correlation id while incrementing attempt metadata.

### Requirement: Retry policies respect idempotency
The HTTP client MUST apply capped exponential backoff for idempotent endpoints and avoid automatic retries for mutations unless explicitly configured with idempotency tokens.

#### Scenario: GET uses capped retries
- **WHEN** a GET request encounters transient network errors
- **THEN** the client retries with exponential backoff up to a configured cap (e.g., 3 attempts) and emits the final attempt count in logs/telemetry.

#### Scenario: Mutations are not retried implicitly
- **WHEN** a POST/PUT/DELETE fails with a 5xx
- **THEN** the client does not auto-retry unless the call is marked idempotent with a token/header, and it surfaces a non-retryable error to the caller.
