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

## ADDED Requirements

### Requirement: Guided lorebook initialization

The Studio MUST offer a project-scoped lorebook initialization wizard inside
a `lore` Inspector tab with URL-backed activation, turning draft material
the author already has into candidate Lore entries through a configured
provider. The wizard MUST accept text the author pastes and content of
already-existing project documents as extraction input, organized as
segments where each segment is one paste or one document's current content,
and MUST present extraction results as candidates — each carrying a
document kind limited to `character` or `world`, a title, suggested
aliases, and a summary body — that are suggestions, not persisted content.
Each segment MUST be extracted by its own `lore-extract` Job under the
synchronous job execution model, recording exactly one usage event per
completed provider request, and cross-segment candidate merging MUST happen
in the wizard session over the completed segment Jobs: same-kind,
same-title candidates collapse to one candidate carrying the union of
suggested aliases, in a deterministic order. Until the author explicitly
confirms, the wizard MUST NOT create any document, revision, or Lore
lifecycle state, and abandoning the wizard MUST leave the project's
lorebook unchanged.

On confirmation, each selected candidate MUST run two existing steps in
sequence — the existing lorebook document creation call, then the existing
Lore alias write path for that candidate's aliases — and the wizard MUST
report each candidate's outcome independently. The two steps MUST NOT be
presented as atomic: when the alias write fails after creation succeeds,
the wizard MUST report the candidate as created with failed aliases, keep
the suggested aliases available for retry, and MUST NOT silently drop
them. Confirmed entries MUST be created at `draft` lifecycle status. With
the trial (mock) provider the wizard MUST still produce deterministic
placeholder candidates per segment and MUST label the session with the
trial-mode wording used by the first-run explainer.

Each input segment MUST be capped at 100,000 Unicode code points. A segment
over the cap, or a segment whose assembled extraction prompt exceeds the
shared UTF-8 byte authority of proposal generation, MUST fail before
provider construction with the stable 422 `GENERATION_CAPACITY_EXCEEDED`
envelope whose details carry `resource: lore_extract_segment`, `limit:
100000`, and an `observed` value bounded to the limit plus one — never
through silent truncation. Any retrieval the wizard performs over project
content MUST behave like the product's full-text search: operator-laden
input safely reduced to strict tokens, irreducible input returning no
results, and every query running as a token-reduced parameterized search.

#### Scenario: Draft material yields candidates

- **GIVEN** a project with a real provider configured
- **WHEN** the author pastes a draft excerpt and runs extraction for that segment
- **THEN** the segment's `lore-extract` Job completes and the wizard presents its candidate entries of kind `character` or `world`, each with a title, suggested aliases, and a summary body
- **AND** no document, revision, or Lore lifecycle state exists yet

#### Scenario: Trial provider yields labeled placeholder candidates

- **GIVEN** a project still on the built-in trial provider
- **WHEN** the author runs the wizard end to end
- **THEN** deterministic placeholder candidates are presented for each segment
- **AND** the session is labeled with the trial-mode wording so the author knows real extraction requires a configured provider

#### Scenario: Nothing persists before confirmation

- **GIVEN** the wizard has presented merged candidates from completed segment Jobs
- **WHEN** the author abandons the wizard without confirming
- **THEN** the project's lorebook, documents, and revisions are unchanged
- **AND** candidates cease to exist with the wizard session; only the segment Jobs' own audit records remain

#### Scenario: Confirmed candidates become draft Lore entries

- **GIVEN** the author selects a subset of the presented candidates and confirms
- **WHEN** confirmation completes
- **THEN** each selected candidate exists as a `character` or `world` document created through the existing creation path at `draft` lifecycle status, followed by the existing alias write for its suggested aliases
- **AND** unselected candidates create nothing
- **AND** each candidate's outcome is reported independently, so one candidate's failure does not hide another's result

#### Scenario: Alias write failure reports partial success

- **GIVEN** a confirmed candidate whose document creation succeeds but whose alias write fails
- **WHEN** the wizard reports that candidate's outcome
- **THEN** it reports the entry as created with failed aliases, not as failed and not as silently alias-less
- **AND** the suggested aliases remain available so the author can retry the alias write

#### Scenario: Confirmed entries reach prompts only through the existing gate

- **GIVEN** a confirmed wizard-created entry is still `draft`
- **WHEN** a proposal is generated whose corpus matches the entry's keys
- **THEN** the entry contributes nothing, exactly like any other `draft` entry
- **WHEN** the author promotes the entry to `stable` using the existing lifecycle editing
- **THEN** the entry participates in keyword-triggered injection like any other `stable` entry

#### Scenario: Over-budget segments fail closed

- **GIVEN** a segment exceeding 100,000 Unicode code points, or a segment whose assembled extraction prompt exceeds the shared UTF-8 byte authority
- **WHEN** extraction is requested for that segment
- **THEN** the request fails before provider construction with 422 `GENERATION_CAPACITY_EXCEEDED` whose details carry `resource: lore_extract_segment`, `limit: 100000`, and an `observed` value of at most the limit plus one
- **AND** no provider work, no usage event, and no partial candidate set is produced for that segment
- **AND** the author is told to split or trim the segment rather than receiving silently truncated results

#### Scenario: Multi-segment candidates merge deterministically

- **GIVEN** two completed segment Jobs whose candidate sets both include a character with the same title
- **WHEN** the wizard presents the merged list
- **THEN** one merged candidate of that kind and title appears, carrying the union of both segments' suggested aliases
- **AND** re-running the merge over the same completed segments yields the same list

#### Scenario: Extraction failures stay inside the provider diagnostics boundary

- **GIVEN** the provider transport receives an error response whose body the provider failure diagnostics boundary discards
- **WHEN** a segment's extraction fails and the wizard reports the failure
- **THEN** the failure surfaces through the Studio error surface with the standard error envelope
- **AND** the discarded upstream body text does not appear in the job error, the envelope, or any author-visible surface
- **AND** no Lore entry is created from the failed run
