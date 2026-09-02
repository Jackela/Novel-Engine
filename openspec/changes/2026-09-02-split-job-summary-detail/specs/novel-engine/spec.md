## MODIFIED Requirements

### Requirement: Synchronous job execution model

Proposal, review, and export jobs MUST execute synchronously within their HTTP
request, and the response MUST carry the job's terminal state (`completed` or
`failed`) — never an in-progress state requiring polling. Jobs and job events
MUST be persisted as an audit log; `running` is an in-request transient, not a
coordination primitive, and the system MUST NOT add lease fields, heartbeats,
or worker registration. At startup, jobs left `running` MUST be marked
`interrupted` with the fixed restart error message and a matching job event.

Project job listings MUST return newest-first strict JobSummary items containing
only `id`, `project_id`, `document_id`, `kind`, `operation`, `status`,
`provider`, `model`, `error`, `retry_of_job_id`, `created_at`, and `updated_at`.
Summary items MUST NOT contain `request`, `result`, or `events`. Complete
proposal, review, export, retry, acceptance, and streamed terminal responses
MUST retain the complete Job payload. Project-scoped Job detail MUST return that
same complete payload with each event as `{id, status, details, created_at}` in
oldest-first order. Because the frontend performs no polling, any move to
asynchronous execution is a new decision that MUST jointly reopen the frontend
behavior contract.

In a JobSummary, `id`, `project_id`, `provider`, `model`, `created_at`, and
`updated_at` MUST be strings; `document_id`, `error`, and `retry_of_job_id` MUST
be string or null. `kind` MUST be one of `proposal`, `review`, `export`, or
`import`; `operation` MUST be one of `continue`, `rewrite`, `generate`, `review`,
`export`, or `import`; and `status` MUST be one of `pending`, `running`,
`completed`, `failed`, or `interrupted`. Timestamps MUST retain the existing
ISO-8601 UTC string serialization.

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

### Requirement: Bounded project job-history traversal

`GET /api/projects/:projectId/jobs` MUST return a strict object containing the
required fields `jobs` and `next_cursor`, where `next_cursor` is an opaque
string or null and each item is the strict JobSummary defined by the
synchronous job model. It MUST accept an optional integer `limit` from 1 through
100, defaulting to 50, and an optional opaque cursor of at most 1024 base64url
characters. Each page MUST return no more than its limit. Jobs MUST be ordered
by `(created_at DESC, id DESC)` and pages MUST use stable keyset traversal rather
than offsets. The list MUST NOT hydrate or return job events.

The cursor MUST be versioned, bound to the route project, and validated as a
canonical base64url token containing a non-negative safe-integer millisecond
timestamp and non-empty position id of at most 128 characters. A malformed,
oversized, truncated, non-canonical, unknown-version, out-of-range, or
cross-project cursor MUST return 422 `VALIDATION_ERROR` identifying the cursor
as invalid, MUST NOT return 500, and MUST NOT reveal whether another project
exists. Invalid zero, over-100, fractional, or non-integer limits MUST return
the same validation code. The cursor is only a position marker; it MUST NOT be
described as a snapshot, authorization grant, or durable public encoding.

Omitting query parameters returns only the newest 50; clients requiring
exhaustive history MUST follow each returned cursor until it is null. The
endpoint MUST continue returning valid bounded pages as total project history
grows, including histories beyond 32,766 jobs. The API MUST NOT add a total
count, automatically traverse pages, or automatically fetch Job detail for
summary items.

The frontend MUST replace jobs and pagination state on a first-page load,
Refresh, visible-Jobs project change, accepted-proposal refresh,
retry-completion refresh, or unknown-outcome audit. It MUST append only through
an explicit accessible load-older action, preserve current data and cursor when
that request fails, coalesce only duplicate same-project/same-cursor older-page
activation, and prevent stale project/request responses from mutating current
state. Every first-page replacement intent MUST invalidate an older-page
request and issue its own cursorless read. Unknown-outcome audit MUST read
exactly the fresh summary first page, MUST settle its existing client-read gate
when that page succeeds, MUST preserve the unknown warning, and MUST NOT claim
attempt correlation, auto-traverse older pages, or request Job detail. Loading
older summaries MUST NOT alter audit status. Within one project, a first-page
failure MUST preserve the last committed summaries and cursor and surface a
retryable error; audit failure MUST also retain its existing failed-gate
behavior. Project change is the exception: it MUST clear old-project summaries
and cursor immediately and MUST NOT restore them if the new-project read fails.

#### Scenario: The default first page is bounded

- **GIVEN** a project has more than 50 jobs
- **WHEN** its jobs are requested without query parameters
- **THEN** the newest 50 summaries are returned in descending timestamp-and-id order
- **AND** `next_cursor` identifies that older history remains

#### Scenario: The maximum page remains bounded

- **GIVEN** a project has more than 100 jobs
- **WHEN** its jobs are requested with `limit=100`
- **THEN** exactly the newest 100 summaries are returned with a non-null cursor

#### Scenario: Equal timestamps traverse deterministically

- **GIVEN** multiple jobs share the same creation timestamp
- **WHEN** the author follows cursors until null
- **THEN** ids break ties in descending order
- **AND** every matching summary appears exactly once with no gaps

#### Scenario: Concurrent inserts do not enter an older traversal

- **GIVEN** the author received a first page and saved its cursor
- **AND** a newer job is inserted before the next request
- **WHEN** the author follows the saved cursor
- **THEN** the new job is not injected into the older page
- **AND** a fresh first-page request shows it

#### Scenario: Deleting the boundary does not block traversal

- **GIVEN** the author received a page and its last returned job is later deleted
- **WHEN** the author follows that page's cursor
- **THEN** older matching summaries are still returned from the saved position

#### Scenario: The terminal page is explicit

- **GIVEN** no matching job exists after the returned page
- **WHEN** the page is serialized
- **THEN** `next_cursor` is present and null

#### Scenario: Invalid cursors fail without scope disclosure

- **GIVEN** a cursor is malformed, non-canonical, truncated, unknown-version, or bound to another project
- **WHEN** the jobs route receives it
- **THEN** the response is 422 `VALIDATION_ERROR` identifying `cursor` as invalid
- **AND** no job data or cross-project existence information is disclosed

#### Scenario: Invalid limits use the validation contract

- **GIVEN** `limit` is zero, greater than 100, fractional, or not an integer
- **WHEN** the jobs route receives it
- **THEN** the response is 422 `VALIDATION_ERROR`
- **AND** no job page is read

#### Scenario: Refresh and load older are distinct

- **GIVEN** the Jobs panel has a first page with older history available
- **WHEN** the author activates Load older jobs
- **THEN** one cursor request appends unique older summaries without clearing the page
- **AND** Refresh instead replaces the list with a fresh summary first page

#### Scenario: A first-page intent supersedes older-page work

- **GIVEN** a cursor-based older-page request is in flight
- **WHEN** Refresh, accepted-proposal refresh, retry-completion refresh, or unknown-outcome audit requires current history
- **THEN** the older append is invalidated and cannot supply or mutate that read
- **AND** one new cursorless summary request owns the replacement intent

#### Scenario: A same-project first-page failure preserves history

- **GIVEN** committed summaries and a next cursor are visible for one project
- **WHEN** a same-project first-page replacement fails
- **THEN** the committed summaries and cursor remain available for retry
- **AND** audit retains its failed gate when applicable

#### Scenario: An older-page failure is recoverable

- **GIVEN** the Jobs panel already shows summaries and has a next cursor
- **WHEN** loading the older page fails
- **THEN** the visible summaries and cursor remain available for retry
- **AND** duplicate activation cannot create parallel page requests

#### Scenario: Project ownership rejects stale pages

- **GIVEN** an older-page request is in flight for one project
- **WHEN** the author switches projects before it resolves
- **THEN** the late response cannot append summaries or cursor state to the new project

#### Scenario: Project switching preserves inspector laziness

- **GIVEN** the author switches projects
- **WHEN** the Jobs inspector remains visible
- **THEN** old summaries and cursor are cleared and exactly one new first page is read
- **BUT WHEN** another inspector is visible
- **THEN** old summaries and cursor are cleared without a jobs request until Jobs opens
- **AND** a later new-project read failure never restores old-project state

#### Scenario: Unknown-outcome audit stays one cheap read

- **GIVEN** a proposal outcome remains unknown and the summary first page has a non-null cursor
- **WHEN** the author performs the required audit
- **THEN** exactly one fresh summary first-page request settles the existing read gate
- **AND** the unknown warning remains visible
- **AND** no older page or Job detail is fetched and no attempt match is claimed

#### Scenario: Terminal keyboard focus remains owned

- **GIVEN** keyboard focus is on Load older jobs
- **WHEN** the terminal older page succeeds and removes that control
- **THEN** focus moves to Refresh jobs
- **BUT WHEN** loading fails
- **THEN** focus stays on the available Load older jobs control for retry

#### Scenario: Long histories remain readable

- **GIVEN** a project contains at least 32,767 jobs
- **WHEN** its first summary page is requested
- **THEN** the endpoint returns a valid bounded page rather than a history-size 500

## ADDED Requirements

### Requirement: Project-scoped complete Job detail

`GET /api/projects/:projectId/jobs/:jobId` MUST require an authenticated Owner
and MUST validate each matched path id as a string from 1 through 128
characters.
It MUST return the existing complete Job payload, including untruncated parsed
request/result and all events in oldest-first order. It MUST NOT mutate the Job,
create an event, or be required before retry.

An unknown project, unknown job, a job belonging to another project, or a
project outside the principal scope MUST return the same 404 `NOT_FOUND`
envelope and stable `Job not found.` message without disclosing whether the
other resource exists. A validly shaped unauthenticated request MUST return
401. Schema validation MUST precede authentication: a matched overlong path
parameter MUST return 422 before authentication and application/store lookup,
including when no session is present. A trailing empty segment that Fastify
binds as an empty parameter MUST likewise return schema-first 422 and MUST NOT
reach authentication or lookup. Persistence unavailability MUST retain the
read-side 503 contract.

The jobs list, retry, unknown-outcome audit, whole-book workflow, and bundled
Jobs panel MUST NOT automatically request detail. External clients needing
removed list fields MUST request only the specifically selected Job rather than
prefetching detail for every summary.

#### Scenario: One scoped detail is complete

- **GIVEN** an authenticated Owner and a Job in the requested project
- **WHEN** the Owner requests that Job detail
- **THEN** the complete Job payload is returned with request, result, and events
- **AND** its events are oldest first

#### Scenario: Detail does not disclose another project

- **GIVEN** a Job id belongs to a different project or does not exist
- **WHEN** it is requested under the route project
- **THEN** the response has the same 404 code, message, and complete envelope as an unknown job
- **AND** no data from the other project is returned

#### Scenario: Detail validation precedes authentication

- **GIVEN** a matched path id is empty or longer than 128 characters and no session is present
- **WHEN** the detail route receives the request
- **THEN** the response is 422 `VALIDATION_ERROR`
- **AND** no Job or project lookup executes

#### Scenario: Valid detail requires authentication

- **GIVEN** both path ids satisfy the detail schema and no session is present
- **WHEN** the detail route receives the request
- **THEN** the response is 401
- **AND** no Job or project lookup executes

#### Scenario: Retry does not need detail

- **GIVEN** a failed or interrupted JobSummary is visible
- **WHEN** the author retries that job
- **THEN** retry executes directly from the durable complete Job record
- **AND** no detail GET is required or issued first

#### Scenario: Whole-book and audit avoid detail fan-out

- **GIVEN** whole-book generation or an unknown-outcome audit reads Job history
- **WHEN** the summary page succeeds
- **THEN** neither workflow requests Job detail
- **AND** no per-summary N+1 read is introduced
