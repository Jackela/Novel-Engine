## ADDED Requirements

### Requirement: Bounded review-history traversal

`GET /api/projects/:projectId/reviews` MUST return a strict object containing
required `reviews` and `next_cursor`, where `next_cursor` is an opaque string
or null. It MUST accept an optional integer `limit` from 1 through 100,
defaulting to 50, and an optional opaque cursor of at most 1024 canonical
base64url characters. Each page MUST return no more than its limit, ordered by
`(created_at DESC, id DESC)` with equal timestamps tie-broken by id, using
stable keyset rather than offset traversal. It MUST NOT return a total count,
automatically follow cursors, or serve work that grows with total stored
review history rather than with the requested page.

Each returned review summary MUST contain only `id`, `project_id`,
`snapshot_id`, provider, model, the fixed summary text, exact non-negative
`issue_count`, and `created_at`. It MUST NOT contain the `issues` array.
Omitting query parameters now returns only the newest 50 summaries; clients
requiring exhaustive summary history MUST follow each cursor until null.

The cursor MUST be versioned and bound to the route project. A malformed,
oversized, non-canonical, truncated, unknown-version, out-of-range, or
cross-project cursor MUST return 422 `VALIDATION_ERROR` identifying `cursor`
as invalid, MUST NOT enter the review store, and MUST NOT reveal whether the
embedded project exists. Invalid zero, over-100, fractional, or non-integer
limits MUST return the same validation code. A cursor is only a position
marker and MUST NOT be treated as a snapshot, authorization grant, or public
durable encoding.

#### Scenario: The default first page is bounded

- **GIVEN** a project has more than 50 stored reviews
- **WHEN** its review history is requested without query parameters
- **THEN** the newest 50 summaries are returned in descending
  timestamp-and-id order
- **AND** `next_cursor` identifies that older history remains
- **AND** no returned summary contains an issues array

#### Scenario: The maximum page remains bounded

- **GIVEN** a project has more than 100 stored reviews
- **WHEN** review history is requested with `limit=100`
- **THEN** exactly the newest 100 summaries are returned
- **AND** the cursor is non-null

#### Scenario: Equal timestamps traverse deterministically

- **GIVEN** two reviews share one creation timestamp
- **WHEN** a page boundary falls between them
- **THEN** the greater id precedes the lesser id
- **AND** continuing from the returned cursor yields the lesser id exactly
  once

#### Scenario: Cursor traversal has no gaps or duplicates

- **GIVEN** the author follows one project's review cursors until null
- **WHEN** each page is appended by review id
- **THEN** every stored review appears exactly once in newest-first order
- **AND** the terminal response contains `next_cursor: null`

#### Scenario: New reviews do not enter an older traversal

- **GIVEN** the author received a first page and retained its cursor
- **AND** another review completes
- **WHEN** the author follows the retained cursor
- **THEN** the newer review is not injected into the older page
- **AND** a fresh first-page read contains it

#### Scenario: Page work stays independent of stored history

- **GIVEN** one project holds 5 stored reviews and another holds 20
- **WHEN** one summary page is served for either project
- **THEN** the statement budget of the read is identical for both
- **AND** no snapshot document body or revision metadata is selected

#### Scenario: Invalid cursor scope is closed

- **GIVEN** a cursor is malformed or bound to another project
- **WHEN** the review-history route receives it
- **THEN** the response is 422 `VALIDATION_ERROR` identifying `cursor` as
  invalid
- **AND** no review data or embedded-project existence is disclosed

#### Scenario: Invalid limits do not read history

- **GIVEN** `limit` is zero, greater than 100, fractional, or not an integer
- **WHEN** the review-history route receives it
- **THEN** the response is 422 `VALIDATION_ERROR`
- **AND** no review page is read

### Requirement: Scoped review-detail read

`GET /api/projects/:projectId/reviews/:reviewId` MUST return the complete
stored assessment for a review that belongs to the route project, including
its full issues array ordered by severity, then code, then snapshot reading
position. A review of another project or a missing review id MUST return the
scoped 404 boundary. The detail read MUST resolve issue order from stored
snapshot positions without selecting revision content or metadata, and list
summaries and cursors MUST NOT be treated as issue authority.

#### Scenario: Detail returns the exact stored findings

- **GIVEN** a completed review with issues on several documents
- **WHEN** its detail is requested for the owning project
- **THEN** every issue is returned with its stored severity, code, message,
  suggestion, and evidence
- **AND** issue order follows severity, code, then snapshot reading position

#### Scenario: Foreign and missing reviews are scoped not-found

- **GIVEN** a stored review of project A
- **WHEN** its detail is requested through project B's route or an unknown id
  is requested
- **THEN** the response is the scoped 404 boundary
- **AND** no cross-project review content is disclosed

#### Scenario: Detail reads transport no manuscript bodies

- **GIVEN** a review snapshot of a multi-chapter project
- **WHEN** its detail is read
- **THEN** no revision content or metadata column is selected
- **AND** the read cost stays independent of chapter body size

### Requirement: Bounded Studio review-history state

The Studio MUST initialize the Review panel from one bounded first summary
page when that panel is the URL-selected Inspector history, and inactive
panels MUST NOT prefetch or publish late outcomes. Older summaries MUST enter
only through an explicit accessible load-older action that appends unique
summaries without clearing the page; its failure MUST preserve committed
summaries and the saved cursor for retry. The newest summary MUST drive one
lazy detail read of the newest assessment's findings; an empty first page
MUST skip it. Completing a review run MUST refresh only the cursorless first
page and the newest detail, MUST NOT traverse older pages, and MUST NOT be
satisfied by a stale response. Project changes MUST abort in-flight review
reads and reject stale responses from publishing into another owner. Loading
older reviews MUST follow the History panel's keyboard focus rules: failure
restores the retryable control, terminal success moves focus to the panel
heading when focus has no connected owner, and a newer author-chosen focus
target is never overridden.

#### Scenario: Lazy activation reads only the selected history

- **GIVEN** the Inspector is on another tab
- **WHEN** review history has not been selected
- **THEN** no review request is made
- **BUT WHEN** the Review tab is selected
- **THEN** one cursorless first page and its newest detail are read

#### Scenario: Load older is explicit and recoverable

- **GIVEN** the Review panel shows a page and a non-null cursor
- **WHEN** the author activates Load older reviews
- **THEN** one cursor request appends unique older summaries without clearing
  the page
- **BUT WHEN** that request fails
- **THEN** existing summaries and the cursor remain available for retry

#### Scenario: Newest findings follow the detail read

- **GIVEN** the first page names review A as newest
- **WHEN** its findings are displayed
- **THEN** they come from review A's detail read rather than the list page
- **AND** a refreshed first page naming review B triggers review B's detail
  instead

#### Scenario: A completed run refreshes only the first page

- **GIVEN** the author has loaded older review summaries
- **WHEN** a review run completes
- **THEN** exactly one cursorless first-page refresh is issued
- **AND** no older page is traversed automatically
- **AND** a stale pre-run response cannot publish summaries or findings

#### Scenario: Project change rejects late review responses

- **GIVEN** a review page or detail request is in flight
- **WHEN** the author switches projects
- **THEN** the request is aborted or its outcome suppressed
- **AND** the new project's review state starts from its own first page
