## ADDED Requirements

### Requirement: Bounded project job-history traversal

`GET /api/projects/:projectId/jobs` MUST return a strict object containing the
required fields `jobs` and `next_cursor`, where `next_cursor` is an opaque
string or null. It MUST accept an optional integer `limit` from 1 through 100,
defaulting to 50, and an optional opaque cursor of at most 1024 base64url
characters. Each page MUST return no more than its limit. Jobs MUST be ordered
by `(created_at DESC, id DESC)` and pages MUST use stable keyset traversal rather
than offsets. Job events on this list endpoint MUST retain newest-first order;
oldest-first single terminal Job responses MUST remain unchanged.

The cursor MUST be versioned, bound to the route project, and validated as a
canonical base64url token containing a non-negative safe-integer millisecond
timestamp and non-empty position id of at most 128 characters. A malformed,
oversized, truncated, non-canonical, unknown-version, out-of-range, or
cross-project cursor MUST return 422 `VALIDATION_ERROR` identifying the cursor
as invalid, MUST NOT return 500, and MUST NOT reveal whether another project
exists. Invalid zero, over-100, fractional, or non-integer limits MUST return
the same validation code. The cursor is only a position marker; it MUST NOT be
described as a snapshot, authorization grant, or durable public encoding.

Omitting query parameters now returns only the newest 50; clients requiring
exhaustive history MUST follow each returned cursor until it is null. The
endpoint MUST continue returning valid bounded pages as total project history
grows, including histories beyond 32,766 jobs. The API MUST NOT add a total
count or automatically traverse pages.

The frontend MUST replace jobs and pagination state on a first-page load,
Refresh, visible-Jobs project change, accepted-proposal refresh,
retry-completion refresh, or unknown-outcome audit. It MUST append only through
an explicit accessible load-older action, preserve current data and cursor when
that request fails, coalesce only duplicate same-project/same-cursor older-page
activation, and prevent stale project/request responses from mutating current
state. Every first-page replacement intent MUST invalidate an older-page
request and issue its own cursorless read. Unknown-outcome audit MUST read
exactly the fresh first page, MUST settle its existing client-read gate when
that page succeeds, MUST preserve the unknown warning, and MUST NOT claim
attempt correlation or auto-traverse older pages. Loading older jobs MUST NOT
alter audit status. Within one project, a first-page failure MUST preserve the
last committed jobs and cursor and surface a retryable error; audit failure MUST
also retain its existing failed-gate behavior. Project change is the exception:
it MUST clear old-project jobs/cursor immediately and MUST NOT restore them if
the new-project read fails.

#### Scenario: The default first page is bounded

- **GIVEN** a project has more than 50 jobs
- **WHEN** its jobs are requested without query parameters
- **THEN** the newest 50 are returned in descending timestamp-and-id order
- **AND** `next_cursor` identifies that older history remains

#### Scenario: The maximum page remains bounded

- **GIVEN** a project has more than 100 jobs
- **WHEN** its jobs are requested with `limit=100`
- **THEN** exactly the newest 100 are returned with a non-null cursor

#### Scenario: Equal timestamps traverse deterministically

- **GIVEN** multiple jobs share the same creation timestamp
- **WHEN** the author follows cursors until null
- **THEN** ids break ties in descending order
- **AND** every matching job appears exactly once with no gaps

#### Scenario: Concurrent inserts do not enter an older traversal

- **GIVEN** the author received a first page and saved its cursor
- **AND** a newer job is inserted before the next request
- **WHEN** the author follows the saved cursor
- **THEN** the new job is not injected into the older page
- **AND** a fresh first-page request shows it

#### Scenario: Deleting the boundary does not block traversal

- **GIVEN** the author received a page and its last returned job is later deleted
- **WHEN** the author follows that page's cursor
- **THEN** older matching jobs are still returned from the saved position

#### Scenario: The terminal page is explicit

- **GIVEN** no matching job exists after the returned page
- **WHEN** the page is serialized
- **THEN** `next_cursor` is present and null

#### Scenario: Invalid cursors fail without scope disclosure

- **GIVEN** a cursor is malformed, non-canonical, truncated, unknown-version,
  or bound to another project
- **WHEN** the jobs route receives it
- **THEN** the response is 422 `VALIDATION_ERROR` identifying `cursor` as invalid
- **AND** no job data or cross-project existence information is disclosed

#### Scenario: Invalid limits use the validation contract

- **GIVEN** `limit` is zero, greater than 100, fractional, or not an integer
- **WHEN** the jobs route receives it
- **THEN** the response is 422 `VALIDATION_ERROR`
- **AND** no job page is read

#### Scenario: Event ordering remains newest first

- **GIVEN** a returned job has multiple transition events
- **WHEN** the page is serialized and documented
- **THEN** those events appear newest first
- **AND** the OpenAPI description states that established order

#### Scenario: Refresh and load older are distinct

- **GIVEN** the Jobs panel has a first page with older history available
- **WHEN** the author activates Load older jobs
- **THEN** one cursor request appends unique older jobs without clearing the page
- **AND** Refresh instead replaces the list with a fresh first page

#### Scenario: A first-page intent supersedes older-page work

- **GIVEN** a cursor-based older-page request is in flight
- **WHEN** Refresh, accepted-proposal refresh, retry-completion refresh, or
  unknown-outcome audit requires current history
- **THEN** the older append is invalidated and cannot supply or mutate that read
- **AND** one new cursorless first-page request owns the replacement intent

#### Scenario: A same-project first-page failure preserves history

- **GIVEN** committed jobs and a next cursor are visible for one project
- **WHEN** Refresh, accepted-proposal refresh, retry-completion refresh, or
  unknown-outcome audit starts a first-page replacement and that read fails
- **THEN** the committed jobs and cursor remain available for retry
- **AND** the error is visible, with audit retaining its failed gate when applicable

#### Scenario: An older-page failure is recoverable

- **GIVEN** the Jobs panel already shows jobs and has a next cursor
- **WHEN** loading the older page fails
- **THEN** the visible jobs and cursor remain available for retry
- **AND** duplicate activation cannot create parallel page requests

#### Scenario: Project ownership rejects stale pages

- **GIVEN** an older-page request is in flight for one project
- **WHEN** the author switches projects before it resolves
- **THEN** the late response cannot append jobs or cursor state to the new project

#### Scenario: Project switching preserves inspector laziness

- **GIVEN** the author switches projects
- **WHEN** the Jobs inspector remains visible
- **THEN** old jobs and cursor are cleared and exactly one new first page is read
- **BUT WHEN** another inspector is visible
- **THEN** old jobs and cursor are cleared without a jobs request until Jobs opens
- **AND** a later new-project read failure never restores the old-project state

#### Scenario: Unknown-outcome audit stays one bounded read

- **GIVEN** a proposal outcome remains unknown and the first jobs page has a
  non-null cursor
- **WHEN** the author performs the required audit
- **THEN** exactly one fresh first-page request settles the existing read gate
- **AND** the unknown warning remains visible
- **AND** older pages are not fetched automatically and no attempt match is claimed

#### Scenario: Terminal keyboard focus remains owned

- **GIVEN** keyboard focus is on Load older jobs
- **WHEN** the terminal older page succeeds and removes that control
- **THEN** focus moves to Refresh jobs
- **BUT WHEN** loading fails
- **THEN** focus stays on the available Load older jobs control for retry

#### Scenario: Long histories remain readable

- **GIVEN** a project contains at least 32,767 jobs
- **WHEN** its first page is requested
- **THEN** the endpoint returns a valid bounded page rather than a history-size 500
