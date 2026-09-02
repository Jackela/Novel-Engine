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
Unicode code points of proposal markdown. A limit breach, deadline, or known body-read
transport failure MUST become a stable server-authored Provider failure without
upstream diagnostics. It MUST record the normal failed proposal outcome and,
for a started stream, end with the normal error frame. It MUST NOT report usage,
persist partial proposal text, retry a stream whose deltas may have escaped, or
reclassify extractor and application programming errors.

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
- **AND** body cleanup waits for at most the fixed cleanup grace

#### Scenario: A response arriving after interruption is discarded

- **GIVEN** an injected transport ignores cancellation and resolves a response
  only after an external abort or absolute deadline has won dispatch
- **WHEN** that late response becomes available
- **THEN** its body is cancelled within the fixed cleanup grace
- **AND** it cannot replace the authoritative interruption cause

#### Scenario: Chapter stream receives the generation floor

- **GIVEN** a chapter draft or revision stream and a configured timeout below
  180 seconds
- **WHEN** the HTTP provider request is dispatched
- **THEN** its absolute deadline is at least 180 seconds
- **AND** its configured silence budgets remain independent shorter ceilings

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
