## MODIFIED Requirements

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
that Job may execute proposal, review, or export work.

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
`proposal`, `review`, or `export`. Import jobs MUST NOT be retryable.

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
- **WHEN** the same key is replayed for proposal, review, or export
- **THEN** the stored terminal Job is returned for every supported kind
- **AND** no provider, review, render, snapshot, assessment, issue, artifact, file, compensation, or usage work runs again

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

### Requirement: Usage accounting for AI requests

Every completed AI proposal request and every successful proposal retry MUST
record exactly one usage event capturing prompt and completion token counts
with an estimated cost. Replaying a terminal retry with the same idempotency
key MUST return its stored Job without recording another usage event or
changing project usage totals. When the provider returns no usage data, token
counts MUST fall back to the unified word-count estimate.

#### Scenario: Provider-reported usage is recorded

- **GIVEN** a provider reports prompt and completion token counts
- **WHEN** the proposal request completes
- **THEN** a usage event records those counts exactly

#### Scenario: Missing usage falls back to word counts

- **GIVEN** a provider returns no usage data
- **WHEN** the proposal request completes
- **THEN** a usage event records token counts derived from the unified word-count definition

#### Scenario: Terminal retry replay does not double-count usage

- **GIVEN** a successful keyed proposal retry already recorded one usage event
- **WHEN** its terminal response is replayed one or more times with the same key
- **THEN** the same Job is returned and its usage event remains singular
- **AND** project request and token totals do not change
