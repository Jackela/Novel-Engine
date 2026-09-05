## ADDED Requirements

### Requirement: Proposal stream downstream backpressure

The streamed proposal response MUST honor downstream writable backpressure.
Each SSE frame MUST be written exactly once and in generation order. When a
frame write reports backpressure, the server MUST NOT request another
application or Provider frame until that response emits `drain`.

The 30-second budget MUST begin immediately after a frame write returns
`false`, MUST apply independently to that drain wait, and MUST be cleared when
the wait settles. It MUST NOT be derived from, reset, or extend any Provider
deadline. While a drain is pending, request cancellation, response failure,
premature response or socket close, and that deadline MUST race with `drain`.
If any interruption wins, the server MUST stop pulling and writing permanently
for that response, MUST cancel unfinished upstream generation, and MUST NOT
allow a later drain event to resume it. A normal response `finish` followed by
`close` MUST NOT be treated as a disconnect.

Among writer-observable request cancellation, response error, premature close,
and drain-deadline events, the first event accepted by the writer's latch MUST
remain authoritative. In particular, an exact response error object MUST NOT
be replaced by a later close, cancellation, drain, deadline, or cleanup
failure; if cleanup also fails, diagnostics MUST retain primary-first ordering.
A drain deadline MUST be reported internally with stable code
`PROPOSAL_STREAM_DRAIN_TIMEOUT`.

#### Scenario: A slow consumer pauses upstream pulls

- **GIVEN** a proposal stream has accepted one frame and its write reports
  backpressure
- **WHEN** no downstream drain has occurred
- **THEN** the server does not request the next application or Provider frame
- **AND** the accepted frame is not written a second time

#### Scenario: Drain resumes exactly once

- **GIVEN** a proposal stream is waiting after a backpressured write
- **WHEN** the response emits `drain` before any interruption
- **THEN** generation resumes with the next frame in order
- **AND** the stream does not duplicate or skip the buffered frame

#### Scenario: Disconnect wins the drain race

- **GIVEN** a backpressured proposal stream has not produced a terminal
  proposal outcome
- **WHEN** the client disconnects before `drain`
- **THEN** upstream generation is cancelled and no further frame is requested
- **AND** a later drain does not resume the stream
- **AND** no job, usage event, or revision is persisted for that interrupted
  generation

#### Scenario: A pre-terminal stalled drain persists nothing

- **GIVEN** a proposal frame write reports backpressure before any terminal job
  is durable
- **WHEN** no drain or earlier writer-observable interruption occurs for 30
  seconds
- **THEN** unfinished generation is cancelled and generator cleanup runs once
- **AND** no job, usage event, or revision is persisted
- **AND** the response is closed and a later drain cannot resume the stream

#### Scenario: A terminal-frame stalled drain preserves the terminal outcome

- **GIVEN** a terminal job is durable and writing its terminal done or error
  frame reports backpressure
- **WHEN** the drain deadline wins
- **THEN** the original terminal job and its already-committed ledger entries
  remain authoritative
- **AND** no additional failed job or usage event is created
- **AND** the client treats the proposal outcome as indeterminate

#### Scenario: An exact response error wins

- **GIVEN** a proposal stream is waiting for drain
- **WHEN** the raw response emits an error before another interruption
- **THEN** that exact error remains the primary failure
- **AND** later close, cancellation, drain, deadline, or generator-cleanup
  failure does not overwrite it

#### Scenario: Normal response completion is not a disconnect

- **GIVEN** every proposal frame has been written and the response finishes
- **WHEN** Node subsequently emits the normal response close event
- **THEN** the close does not cancel generation or create a stream failure

## MODIFIED Requirements

### Requirement: Whole-book generation loop

The Studio MUST offer a whole-book generation mode driven by the frontend over
the existing proposal and accept endpoints: it drafts a proposal for the next
chapter needing one, accepts it automatically, and proceeds in reading order.
The loop MUST be stoppable and resumable. Stop or a project-identity change
before an in-flight proposal durably produces its terminal job MUST abort that
proposal before it lands a job or usage event, MUST prevent any later chapter
from starting, and MUST preserve every acceptance that already completed. An
atomic acceptance already executing MAY complete; if it does, that chapter is
counted as preserved completed work.

If Stop or a transport failure occurs after a completed terminal job and its
usage event are durable but before the frontend observes its done frame, that
job and usage event MUST remain durable, but the loop MUST NOT auto-accept it
or start a later chapter. For the still-current project, the Studio MUST enter
an outcome-unknown stopped or failed state and complete a non-coalesced
job-history audit read started after the client observes stream settlement.
Proposal generation and whole-book resume MUST remain unavailable until that
read succeeds. If the read fails, the unknown state MUST remain and only the
audit read may be retried. Success MUST NOT be presented as proof that the old
server handler is quiescent or that its terminal job is present in the
snapshot. An explicit later proposal attempt MAY create another auditable job
and usage event.

#### Scenario: The loop advances chapter by chapter

- **GIVEN** a project with an outline and one completed chapter
- **WHEN** the whole-book loop runs
- **THEN** each subsequent chapter receives a generated proposal that is accepted automatically in reading order

#### Scenario: Stop preserves completed work

- **GIVEN** the loop has accepted two chapters and is drafting the next without
  a durable terminal proposal job
- **WHEN** the author stops the loop
- **THEN** the two accepted chapters remain
- **AND** the in-flight draft persists no job or usage event
- **AND** no later chapter starts

#### Scenario: Stop after terminal persistence does not guess

- **GIVEN** a proposal's terminal job and usage event are durable but its done
  frame has not completed the response
- **WHEN** the author stops the whole-book loop or the transport fails
- **THEN** the durable job and usage event remain
- **AND** the loop does not auto-accept that proposal or start a later chapter
- **AND** a client-settlement-ordered job-history audit read succeeds before an
  author may explicitly generate another proposal

### Requirement: Streaming proposal generation

The API MUST expose `POST /api/projects/:projectId/documents/:documentId/ai-proposals/stream`,
authenticated like every other write surface (session cookie plus CSRF
header), accepting the same request body as the synchronous proposal
endpoint. On success it MUST answer `200` with `text/event-stream` frames of
single-line JSON events: `{"type":"delta","text":…}` for each markdown
piece, then either `{"type":"done","job":…}` carrying the same job payload
shape as the synchronous endpoint, or `{"type":"error","error":{"code":…,"message":…}}`.
Invalid input, unknown documents, in-flight conflicts, and providers without
the streaming capability MUST be rejected with the normal error envelope
before the stream starts. A completed stream MUST land the same way as the
synchronous endpoint (a completed job plus exactly one usage event); a
provider failure mid-stream MUST record a failed job and end the stream with
an error frame without fabricating text. A client disconnect or request abort
before a terminal proposal outcome is durably produced MUST abort the upstream
provider request and persist nothing. A transport interruption after a
terminal job is durable MUST NOT roll that job or any associated usage event
back. The synchronous proposal endpoint MUST remain unchanged and the proposal
contract MUST hold: nothing mutates the manuscript until an explicit accept.

The Studio MUST consider a streamed proposal outcome known only after it has
fully parsed a terminal `done` or `error` frame, or received a normal pre-stream
error envelope. Cancellation, network failure, premature EOF, or protocol
failure before a terminal frame is parsed MUST be classified as `proposal
outcome unknown`; the Studio MUST NOT claim that nothing was persisted.

For the still-current project, the Studio MUST discard any partial preview,
stop automatic acceptance and whole-book continuation, and complete a new,
non-coalesced job-history audit request that starts after the client observes
stream settlement. Until that refresh succeeds, controls that could start
another proposal MUST remain unavailable. If the refresh fails, the outcome
MUST remain unknown and only the audit refresh may be retried. A same-project
document-identity change MUST still audit the interrupted document's unknown
outcome while preventing its stale proposal state from publishing into the
newly selected document. A project-identity change MUST prevent old results
from publishing into or triggering reads for the new project.

Job history is audit evidence and MUST NOT be treated as proof that a
particular job belongs to the ambiguous request or that the server-side stream
is quiescent. The old stream MAY finish cleanup or land a terminal job after
this client-ordered snapshot, so the proposal outcome MUST remain unknown.
After a successful refresh, the Studio MUST warn that the earlier attempt
might already be durable and that generating again can create another job and
usage event. Only an explicit author action labelled as generating another
proposal may start that new attempt; the Studio MUST NOT automatically retry,
select, or accept an unobserved job.

#### Scenario: Deltas stream, then done carries the job

- **GIVEN** an owner session and a document with a current revision
- **WHEN** the owner requests a streamed proposal from a provider with the
  streaming capability
- **THEN** the response is a `text/event-stream` of delta frames whose
  concatenation equals the persisted proposal markdown
- **AND** the stream ends with a done frame whose job payload is a completed
  proposal job with exactly one usage event recorded

#### Scenario: Abort persists nothing

- **GIVEN** a proposal stream is running without a durable terminal outcome
- **WHEN** the client disconnects or aborts its request
- **THEN** the upstream provider request is aborted
- **AND** no job, no usage event, and no revision is persisted for the
  interrupted stream

#### Scenario: Terminal response loss triggers an audit snapshot without inference

- **GIVEN** proposal generation has already durably produced a terminal job and
  corresponding done or error frame
- **WHEN** the response fails before response completion and the client does
  not observe that frame
- **THEN** the durable terminal job remains authoritative
- **AND** a new job-history audit read started after client-observed stream
  settlement succeeds before proposal actions are re-enabled
- **AND** refreshed rows are not claimed as a unique match for the interrupted
  request or proof that the server stream is quiescent
- **AND** the Studio does not automatically retry or accept the unobserved job

#### Scenario: Audit refresh failure keeps proposal actions gated

- **GIVEN** a proposal stream ends with an unobserved terminal outcome
- **WHEN** the client-settlement-ordered job-history audit read fails
- **THEN** the Studio remains in the proposal-outcome-unknown state
- **AND** proposal generation and whole-book resume remain unavailable
- **AND** the available recovery retries only the job-history audit read

#### Scenario: Same-project document change still takes an audit snapshot

- **GIVEN** document A has an in-flight proposal in a still-current project
- **WHEN** the author selects document B before A's terminal frame is observed
- **THEN** A's partial preview and terminal result never publish into B
- **AND** a client-settlement-ordered job-history audit read for the current
  project must succeed before another proposal can start

#### Scenario: Provider failure mid-stream records a failed job

- **GIVEN** a proposal stream has already delivered deltas
- **WHEN** the provider fails before completing the stream, or the
  accumulated markdown fails the prose validation after completion
- **THEN** the stream ends with an error frame carrying the failure message
- **AND** a failed proposal job with an empty proposal markdown is recorded
- **AND** no usage event is recorded for the failed stream
