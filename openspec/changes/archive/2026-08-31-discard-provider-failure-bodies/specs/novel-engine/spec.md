## MODIFIED Requirements

### Requirement: Provider transient failure handling
For synchronous structured generation calls, both HTTP providers MUST share
one retry policy with an identical retryable set: HTTP 429, 500, 502, 503,
504, transport timeout, and malformed JSON responses are retried up to the
configured limit (default three total attempts, with one-second spacing
between attempts); every other error fails immediately without retry. Retry
decisions MUST read structured error fields (status code, timeout,
retryability), never substring matches on human-readable message text, and
both HTTP providers MUST share the same retry module. Synchronous generation
steps (`chapter_draft`, `chapter_revision`) MUST be granted a timeout floor of
180 seconds, and the enclosing server request timeout MUST NOT be shorter
than that floor.

#### Scenario: Transient error is retried
- **GIVEN** the provider answers 429 once and then succeeds
- **WHEN** a proposal is requested
- **THEN** the job completes with a proposal
- **AND** the transient failure is not surfaced as a job error

#### Scenario: Persistent failure exhausts retries
- **GIVEN** the provider answers 503 on every attempt
- **WHEN** a proposal is requested
- **THEN** the job fails with the provider error after three total attempts by default

#### Scenario: Non-retryable failure is immediate
- **GIVEN** the provider answers 401
- **WHEN** a proposal is requested
- **THEN** the job fails after one attempt

#### Scenario: Generation timeout floor
- **GIVEN** a chapter revision generation on an HTTP provider
- **WHEN** the request is dispatched
- **THEN** the provider call is granted at least 180 seconds
- **AND** the enclosing HTTP request does not time out sooner

## ADDED Requirements

### Requirement: Untrusted Provider failure diagnostics boundary
When an HTTP Provider response has a non-success HTTP status, its upstream
response body MUST be treated as untrusted diagnostics. The adapter MUST
cancel and discard that body without consuming its contents. The system MUST
NOT copy body-derived text into
application error messages, persisted job errors or event details, API
payloads, SSE frames, author-visible text, or application logs. It MUST
instead expose a stable server-authored Provider failure after successful
disposal, derived only from trusted local context and the normalized failure
class or numeric HTTP status. If response cancellation itself raises an
unexpected local error, that error MUST remain visible, MUST NOT be
reclassified or retried from the upstream HTTP status, and MUST NOT gain any
body-derived diagnostic text. Discarding the body MUST NOT remove the
structured status used by the Provider transient failure handling
Requirement.

#### Scenario: Persistent synchronous failure stays inside the boundary
- **GIVEN** either HTTP Provider returns 503 with a body containing a unique sensitive marker on every attempt
- **WHEN** a proposal exhausts the default attempt budget
- **THEN** status 503 drives three total attempts
- **AND** the failed job, event, and JSON payload use a stable server-authored error
- **AND** no body-derived text or sensitive marker is persisted, logged, or returned

#### Scenario: Non-retryable body stays private
- **GIVEN** either HTTP Provider returns 401 with a body containing a unique sensitive marker
- **WHEN** a proposal is requested
- **THEN** exactly one attempt occurs
- **AND** the failed job and public error use a stable server-authored message
- **AND** no body-derived text or sensitive marker crosses the boundary

#### Scenario: Streaming HTTP failure uses the same safe boundary
- **GIVEN** a streaming HTTP Provider returns a non-success response whose body contains a unique sensitive marker
- **WHEN** the proposal stream ends with a `PROVIDER_FAILED` frame and records a failed job
- **THEN** the frame, job, and event use the stable server-authored message
- **AND** no body-derived text or sensitive marker is persisted, logged, or returned
- **AND** no proposal text or usage event is fabricated
