## MODIFIED Requirements

### Requirement: Provider transient failure handling

For synchronous structured generation calls, both HTTP providers MUST share
one retry policy with an identical retryable set: HTTP 429, 500, 502, 503,
504, transport timeout (including an absolute response deadline), and malformed
JSON responses are retried up to the configured limit (default three total
attempts, with one-second spacing between attempts); every other error fails
immediately without retry. Retry decisions MUST read structured error fields
(status code, timeout, retryability), never substring matches on
human-readable message text, and both HTTP providers MUST share the same retry
module. A retryable per-attempt deadline failure MUST NOT record the normal
failed proposal outcome until the attempt budget is exhausted. Synchronous
generation steps (`chapter_draft`, `chapter_revision`) MUST be granted a
timeout floor of 180 seconds, and the enclosing server request timeout MUST
NOT be shorter than that floor.

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

### Requirement: Untrusted Provider failure diagnostics boundary

When an HTTP Provider response has a non-success HTTP status, its upstream
response body MUST be treated as untrusted diagnostics. The adapter MUST
cancel and discard that body without consuming its contents. The system MUST
NOT copy body-derived text into application error messages, persisted job
errors or event details, API payloads, SSE frames, author-visible text, or
application logs. It MUST instead register a stable server-authored Provider
failure before body cleanup, derived only from trusted local context and the
normalized failure class or numeric HTTP status. Once registered, that status
failure MUST remain authoritative if response cancellation rejects or exceeds
the fixed one-second cleanup grace. An unexpected local error raised while
constructing or registering the status failure MUST remain visible, MUST NOT be
reclassified or retried from the upstream HTTP status, and MUST NOT gain
body-derived diagnostic text. Discarding the body MUST NOT remove the
structured status used by the Provider transient failure handling Requirement.

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

## ADDED Requirements

### Requirement: Bounded provider response lifecycle

Every HTTP provider response MUST have one absolute deadline that starts before
transport dispatch and covers connection establishment, response headers, and
complete body consumption. Chapter draft and revision streams MUST receive the
same effective timeout floor of 180 seconds as synchronous generation. The
existing first-event and between-event silence budgets MUST remain additional
ceilings and MUST NOT reset or extend the absolute deadline.

An external abort MUST participate explicitly in dispatch, response-body, and
stream-iteration waits, including when an injected transport or body ignores
its signal. A pre-aborted request MUST NOT dispatch. The first timeout,
cancellation, size, or transport cause MUST remain authoritative while reader
and iterator cleanup is awaited without replacing that cause.

The server MUST consume at most 8 MiB from one synchronous JSON response or one
complete SSE response, at most 1 MiB from one SSE event, and at most 1,000,000
Unicode code points of proposal markdown. A limit breach, deadline, or known
body-read transport failure MUST become a stable server-authored Provider
failure without upstream diagnostics. A retryable synchronous deadline MUST
enter the existing Provider transient failure policy, and the normal failed
proposal outcome MUST be recorded only if that attempt budget is exhausted. A
started stream MUST end with the normal error frame. The system MUST NOT report
usage, persist partial proposal text, retry a stream whose deltas may have
escaped, or reclassify extractor and application programming errors. All
response-body, reader, and iterator cleanup MUST settle or yield to the
authoritative failure within a fixed one-second cleanup grace.

#### Scenario: Absolute deadline covers response setup and body

- **GIVEN** an HTTP provider stalls before returning headers or keeps sending
  frames within the silence budget without completing
- **WHEN** the effective provider deadline elapses
- **THEN** the transport is aborted with the stable provider timeout
- **AND** the deadline has not reset after any response byte or frame

#### Scenario: External cancellation wins an uncooperative wait

- **GIVEN** a request is already aborted or its external signal aborts while
  an injected transport or response body ignores that signal
- **WHEN** dispatch, body consumption, or stream iteration is waiting
- **THEN** the wait stops without waiting for the provider deadline
- **AND** a pre-aborted request performs no transport dispatch
- **AND** no stream outcome is reported after cancellation, including after
  the final delta or while iterator cleanup is running
- **AND** reader and iterator cleanup cannot replace the cancellation cause

#### Scenario: Failure response cleanup preserves HTTP status

- **GIVEN** a non-success provider response whose body cancellation rejects or
  never settles
- **WHEN** synchronous or streaming generation rejects the response
- **THEN** the HTTP status failure remains authoritative
- **AND** body cleanup waits for at most one second

#### Scenario: A response arriving after interruption is discarded

- **GIVEN** an injected transport ignores cancellation and resolves a response
  only after an external abort or absolute deadline has won dispatch
- **WHEN** that late response becomes available
- **THEN** its body is cancelled within the one-second cleanup grace
- **AND** it cannot replace the authoritative interruption cause

#### Scenario: Chapter stream receives the generation floor

- **GIVEN** a chapter draft or revision stream and a configured timeout below
  180 seconds
- **WHEN** the HTTP provider request is dispatched
- **THEN** its absolute deadline is at least 180 seconds
- **AND** its configured silence budgets remain independent ceilings that cannot
  extend the absolute deadline

#### Scenario: Mid-body transport failure lands normally

- **GIVEN** a successful HTTP response whose body fails while being read
- **WHEN** the failure is a known fetch transport rejection
- **THEN** it becomes a sanitized Provider failure
- **AND** the proposal records a failed job and no usage event
- **AND** a started proposal stream ends with its normal error frame

#### Scenario: Synchronous response exceeds its byte budget

- **GIVEN** a successful HTTP provider response whose JSON body exceeds 8 MiB
- **WHEN** structured generation consumes the body
- **THEN** generation fails immediately with a stable size-limit failure
- **AND** the original response is consumed at most once

#### Scenario: Stream event or total body exceeds its byte budget

- **GIVEN** an HTTP provider stream whose single event exceeds 1 MiB or whose
  total response exceeds 8 MiB
- **WHEN** the shared SSE parser reaches the applicable boundary
- **THEN** the upstream transport is aborted with a stable size-limit failure
- **AND** no usage outcome or completed proposal is recorded

#### Scenario: Mixed SSE newline boundaries preserve event bytes

- **GIVEN** an SSE stream separates events with any combination matched by
  `\r?\n\r?\n`, including a separator split across body chunks
- **WHEN** the shared parser measures and emits an event
- **THEN** the complete separator is excluded from the event byte count
- **AND** an event of exactly 1 MiB is accepted while one byte more is rejected

#### Scenario: Proposal markdown exceeds its semantic budget

- **GIVEN** any provider returns more than 1,000,000 Unicode code points of
  proposal markdown synchronously or across streamed deltas
- **WHEN** the proposal application boundary receives that output
- **THEN** the proposal fails before oversized text is persisted
- **AND** a stream emits no further delta after the limit would be crossed
- **AND** one astral character counts once even when its surrogate pair is
  split across consecutive deltas
