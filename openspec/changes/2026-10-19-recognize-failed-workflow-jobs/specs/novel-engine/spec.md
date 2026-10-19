## MODIFIED Requirements

### Requirement: Synchronous job execution model

Proposal, review, export, and lore-extract jobs MUST execute synchronously
within their HTTP request, and the response MUST carry the job's terminal
state (`completed` or `failed`) — never an in-progress state requiring
polling. Jobs and job events MUST be persisted as an audit log; `running` is
an in-request transient, not a coordination primitive, and the system MUST
NOT add lease fields, heartbeats, or worker registration. At startup, jobs
left `running` MUST be marked `interrupted` with the fixed restart error
message and a matching job event.

Project job listings MUST return newest-first strict JobSummary items containing
only `id`, `project_id`, `document_id`, `kind`, `operation`, `status`,
`provider`, `model`, `error`, `retry_of_job_id`, `created_at`, and `updated_at`.
Summary items MUST NOT contain `request`, `result`, or `events`. Complete
proposal, review, export, lore-extract, retry, acceptance, and streamed
terminal responses MUST retain the complete Job payload. Project-scoped Job
detail MUST return that same complete payload with each event as
`{id, status, details, created_at}` in oldest-first order. Because the
frontend performs no polling, any move to asynchronous execution is a new
decision that MUST jointly reopen the frontend behavior contract.

In a JobSummary, `id`, `project_id`, `provider`, `model`, `created_at`, and
`updated_at` MUST be strings; `document_id`, `error`, and `retry_of_job_id`
MUST be string or null. `kind` MUST be one of `proposal`, `review`, `export`,
`lore-extract`, or `import`; `operation` MUST be one of `continue`,
`rewrite`, `generate`, `review`, `export`, `extract`, or `import`; and
`status` MUST be one of `pending`, `running`, `completed`, `failed`, or
`interrupted`. Timestamps MUST retain the existing ISO-8601 UTC string
serialization.

#### Scenario: One request reaches a terminal state

- **GIVEN** a proposal request
- **WHEN** the HTTP response is returned
- **THEN** the complete job it reports is `completed` or `failed`
- **AND** no client polling is required to learn the outcome

#### Scenario: Restart recovery

- **GIVEN** a job is `running` when the process exits
- **WHEN** the server starts again
- **THEN** the job is marked `interrupted` with the fixed restart error message and a matching job event
- **AND** the job becomes eligible for retry

#### Scenario: Events record every transition

- **GIVEN** one proposal that succeeds and one that fails
- **WHEN** their complete scoped Job details are requested
- **THEN** each carries its event stream with `{id, status, details, created_at}`
- **AND** events appear oldest first while the history list returns summaries only

#### Scenario: History returns strict summaries

- **GIVEN** persisted jobs contain large request, result, and event details
- **WHEN** their project history page is listed
- **THEN** each item contains exactly the twelve JobSummary fields
- **AND** request, result, and events are absent rather than null or optional

#### Scenario: One detail preserves the audit object

- **GIVEN** a persisted job has request, result, error, and transition events
- **WHEN** its scoped detail is requested
- **THEN** the complete values are returned without truncation
- **AND** its events appear oldest first

Complete failed Review and Export Jobs MAY carry `null` for their absent
`result.review_id` or `result.export_id`, respectively. The Studio MUST
recognize those terminal failures and expose their recorded error rather
than treating a null result ID as a malformed response. Non-string, non-null
values for those result IDs MUST remain invalid.

#### Scenario: A known workflow failure has no result artifact

- **GIVEN** Review or Export execution records a failed complete Job with its corresponding result ID set to null
- **WHEN** the Studio receives its creation, detail, or retry response
- **THEN** it recognizes the failed Job and exposes the recorded operation error
- **AND** it does not claim that the response is unrecognizable solely because no result artifact exists


### Requirement: Job retry chain

Retry MUST be limited to jobs in `failed` or `interrupted` state; any other
state is rejected for a new attempt. Every
`POST /api/projects/:projectId/jobs/:jobId/retry` request MUST carry a required
case-sensitive `Idempotency-Key` header of 16 through 128 ASCII characters
matching `[A-Za-z0-9._~-]+`. Missing or invalid keys MUST return the unified
422 validation response and MUST NOT reserve or execute work. A body field MUST
NOT substitute for the header.

For a key not previously used with the authenticated owner, route project, and
source Job, retry MUST create one new job that inherits kind, operation,
provider, model, and request payload from the source, starts `running`, links
to the source via `retry_of_job_id`, durably records the key, and records a
first job event naming the source. The source Job is never mutated. Admission
MUST be concurrency-safe and durable across restart: at most one retry Job may
exist for the same owner/project/source/key, and only the request that creates
that Job may execute proposal, review, export, or lore-extract work.

A replay of the same key after its retry Job is `completed`, `failed`, or
`interrupted` MUST return 200 with that same complete Job and its existing
events. It MUST NOT execute operation work, create another Job or event, change
timestamps, or add usage or workflow evidence. A replay while that retry Job is
`running` MUST return the existing 409 `OPERATION_IN_FLIGHT` with
`Retry-After: 1`, MUST create no evidence, and MAY be replayed later with the same key. A
different key represents an explicit new author attempt and MUST NOT be
deduplicated with a settled earlier key, while remaining subject to the
existing retryability, project-pipeline, and capacity rules.

The identity MUST be scoped without disclosure across owners and projects. It
MUST apply when the source is either a fresh or earlier retry Job of kind
`proposal`, `review`, `export`, or `lore-extract`. Import jobs MUST NOT be
retryable.

The Studio MUST generate a bounded cryptographically random key before
dispatch and retain it for the owner/project/source attempt across ambiguous
transport failure, timeout, abort, every 409/503, project navigation, and reload
within the browser-tab session. It MUST reuse that key when the same unresolved
attempt is replayed, MUST NOT send it for another owner/project/source, and
MUST clear it after a terminal 200 response or a 401, 403, 404, or 422
response. Logout or owner-session replacement MUST clear retained
keys. After a known terminal result, a later explicit retry MUST generate a new
key. Late responses MUST obey existing project/request ownership and MUST NOT
mutate another project's visible state.

#### Scenario: Retry chains a new job

- **GIVEN** a failed proposal job and a valid key not used for that source Job
- **WHEN** it is retried and the retry completes
- **THEN** one new job exists with `retry_of_job_id` pointing at the source
- **AND** the source remains recorded as failed with its events intact

#### Scenario: A lost terminal response is replayed

- **GIVEN** a proposal retry reached a terminal Job but its response was lost
- **WHEN** the client repeats the source Job retry with the same key
- **THEN** the response returns that exact terminal Job with its complete events
- **AND** no provider call, Job, event, proposal, or usage evidence is added

#### Scenario: A running keyed attempt is not duplicated

- **GIVEN** one keyed retry Job is still running
- **WHEN** a concurrent request repeats the same owner, project, source Job, and key
- **THEN** it receives 409 `OPERATION_IN_FLIGHT` with `Retry-After: 1`
- **AND** only the existing retry Job remains eligible to execute

#### Scenario: Concurrent reservation has one winner

- **GIVEN** no retry Job yet exists for one owner/project/source/key identity
- **WHEN** two concurrent requests try to reserve it
- **THEN** exactly one running retry Job and first event are created
- **AND** the losing request replays the winner or reports it in flight without executing work

#### Scenario: Reservation event failure is not a replay winner

- **GIVEN** a new keyed retry inserts its Job row but the required first event cannot be inserted
- **WHEN** reservation fails
- **THEN** the complete reservation transaction rolls back with no keyed retry Job
- **AND** the constraint failure is not normalized as a winning concurrent request

#### Scenario: Restart preserves keyed identity

- **GIVEN** a keyed retry Job was running when the server stopped
- **WHEN** startup recovery marks it interrupted and the same key is replayed
- **THEN** the recovered interrupted Job is returned with its existing events
- **AND** no second retry Job or operation execution is created

#### Scenario: A different key is a new author attempt

- **GIVEN** a keyed retry attempt is terminal and its source remains retryable
- **WHEN** the author explicitly retries that source with a different valid key
- **THEN** a distinct retry Job may be created under the existing admission rules
- **AND** it is not mistaken for replay of the earlier attempt

#### Scenario: Retry identity is scoped

- **GIVEN** the same key text is used for another source Job, project, or owner
- **WHEN** an authorized retry is requested in that distinct scope
- **THEN** it does not collide with or return the first scope's retry Job
- **AND** an unauthorized project request retains the existing non-disclosing response

#### Scenario: Proposal, review, and export replay stored outcomes only

- **GIVEN** a terminal keyed retry whose source was a fresh or prior retry Job
- **WHEN** the same key is replayed for proposal, review, export, or lore-extract
- **THEN** the stored terminal Job is returned for every supported kind
- **AND** no provider, extraction, review, render, snapshot, assessment, issue, artifact, file, compensation, or usage work runs again

#### Scenario: Only terminal failures are retryable

- **GIVEN** a completed job and a valid key not previously reserved for it
- **WHEN** retry is requested
- **THEN** the request is rejected and no new job is created

#### Scenario: Import jobs are not retryable

- **GIVEN** a job of kind import and a valid unreserved key
- **WHEN** retry is requested
- **THEN** the request is rejected with an explicit error

#### Scenario: Old clients fail closed

- **GIVEN** a client omits `Idempotency-Key` or sends it only in the body
- **WHEN** it requests retry
- **THEN** the response is the unified 422 validation error
- **AND** no retry Job, event, provider call, or usage event is created

#### Scenario: Header validation precedes authentication

- **GIVEN** an anonymous request omits or malforms `Idempotency-Key`
- **WHEN** it requests retry through the declared route schema
- **THEN** it receives the same unified 422 validation response without reservation

#### Scenario: Project switching retains only the scoped attempt

- **GIVEN** a retry response is unknown and the author switches projects
- **WHEN** the author returns and replays the same source Job
- **THEN** the retained key for that owner/project/source is reused
- **AND** neither its request nor a late response mutates the other project's state

#### Scenario: A failed workflow retry settles its attempt key

- **GIVEN** a Review or Export retry returns a complete failed Job with a null result ID
- **WHEN** the author explicitly retries the same source Job after that known terminal response
- **THEN** the Studio generates a different attempt key and refreshes the Job history
- **AND** the new attempt can execute after the underlying operation recovers rather than replaying the settled failure
