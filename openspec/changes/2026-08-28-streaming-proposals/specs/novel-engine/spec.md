## ADDED Requirements

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
an error frame without fabricating text; a client disconnect MUST abort the
upstream provider request and persist nothing. The synchronous proposal
endpoint MUST remain unchanged and the proposal contract MUST hold: nothing
mutates the manuscript until an explicit accept.

#### Scenario: Deltas stream, then done carries the job

- **GIVEN** an owner session and a document with a current revision
- **WHEN** the owner requests a streamed proposal from a provider with the
  streaming capability
- **THEN** the response is a `text/event-stream` of delta frames whose
  concatenation equals the persisted proposal markdown
- **AND** the stream ends with a done frame whose job payload is a completed
  proposal job with exactly one usage event recorded

#### Scenario: Abort persists nothing

- **GIVEN** a proposal stream is running
- **WHEN** the client disconnects (or aborts its request) mid-stream
- **THEN** the upstream provider request is aborted
- **AND** no job, no usage event, and no revision is persisted for the
  interrupted stream

#### Scenario: Provider failure mid-stream records a failed job

- **GIVEN** a proposal stream has already delivered deltas
- **WHEN** the provider fails before completing the stream, or the
  accumulated markdown fails the prose validation after completion
- **THEN** the stream ends with an error frame carrying the failure message
- **AND** a failed proposal job with an empty proposal markdown is recorded
- **AND** no usage event is recorded for the failed stream
