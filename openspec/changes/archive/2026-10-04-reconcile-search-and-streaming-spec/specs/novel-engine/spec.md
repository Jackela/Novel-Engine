## MODIFIED Requirements

### Requirement: Full-text search over current content

The system MUST expose project-scoped full-text search over document titles
and current content through a search endpoint, with the index synchronized
transactionally on every document create, save, and delete. Search input
MUST be reduced to safe tokens — case-folded word tokens, de-duplicated
preserving first occurrence, at most 3 tokens, combined with AND semantics —
and FTS5 operators, column filters, NEAR groups, wildcards, and punctuation
MUST NOT reach the match expression. Each result MUST identify the document
and carry its title and a plain-text excerpt of at most a 16-token window
around the best match, with truncation marked by an ellipsis and no highlight
markup. Results MUST be ordered by relevance rank and delivered in bounded
pages: the page size defaults to 30 and MUST NOT exceed 100 items; each
response MUST report the total number of matching documents and the offset of
the next page — null exactly when every match has been delivered — and a
query that reduces to no tokens MUST return an empty result list. All
full-text access MUST be centralized in a single search module, and index
writes and deletes MUST occur in the same transaction as the owning document
change.

#### Scenario: Ranked snippets for matching content

- **GIVEN** several documents of one project contain the word "lantern"
- **WHEN** the project search endpoint is called with `q=lantern`
- **THEN** matching documents are returned ordered by relevance rank
- **AND** each result carries the document identifier, title, and a
  plain-text excerpt
- **AND** no excerpt contains highlight markup such as `<mark>`

#### Scenario: Operator-laden input is safely reduced

- **GIVEN** a query stuffed with FTS5 syntax such as
  `dragon OR title:( NEAR(a b) wolf* ) "quotes"`
- **WHEN** the search runs
- **THEN** only the reduced quoted word tokens are matched with AND semantics
- **AND** no operator, column filter, NEAR group, or wildcard is executed as
  FTS5 syntax
- **AND** the response succeeds without error

#### Scenario: Unreducible input returns no results

- **GIVEN** a query that reduces to no word tokens, such as empty or
  punctuation-only input
- **WHEN** the search runs
- **THEN** the response succeeds with an empty result list
- **AND** no match expression is evaluated

#### Scenario: The index never serves stale content

- **GIVEN** a document matched an earlier search and is then deleted
- **WHEN** the same search runs again
- **THEN** the deleted document is absent from the results
- **AND** the deletion and its index cleanup committed in the same transaction

#### Scenario: Result count is bounded

- **GIVEN** more than one page of documents matches the reduced tokens
- **WHEN** the search runs without an explicit page size
- **THEN** the response contains at most 30 results
- **AND** it reports the total number of matching documents
- **AND** it reports the next page's offset until every match has been
  delivered

### Requirement: Bounded provider response lifecycle

Every HTTP provider response MUST have one absolute deadline that starts before
transport dispatch and covers connection establishment, response headers, and
complete body consumption of synchronous responses. For a stream, the deadline
MUST cover dispatch through the first delivered event, and every delivered
event MUST re-arm it, so the budget bounds dispatch plus silence rather than
the total wall time of a healthy stream; the first-event and between-event
silence budgets MUST remain additional ceilings. Chapter draft and revision
streams MUST receive the same effective timeout floor of 180 seconds as
synchronous generation.

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

- **GIVEN** an HTTP provider stalls before returning headers or before the
  first stream event
- **WHEN** the effective provider deadline elapses
- **THEN** the transport is aborted with the stable provider timeout

#### Scenario: A healthy stream re-arms the deadline per event

- **GIVEN** a stream delivers events at intervals inside its silence budgets
- **WHEN** the stream outlives the original dispatch deadline
- **THEN** every delivered event re-arms the deadline and the stream is not
  aborted
- **AND** the stream can reach its normal terminal event and outcome

#### Scenario: Over-silent streams still abort

- **GIVEN** a started stream stops delivering events
- **WHEN** its silence exceeds the re-armed deadline or a configured silence
  budget
- **THEN** the transport is aborted with the stable provider timeout

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
