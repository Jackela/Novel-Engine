## ADDED Requirements

### Requirement: Bounded project catalog traversal

`GET /api/projects` MUST return a strict object containing required
`projects` and `next_cursor`, where `next_cursor` is an opaque string or
null. It MUST accept an optional integer `limit` from 1 through 100,
defaulting to 50, and an optional opaque cursor of at most 1024 canonical
base64url characters. Each page MUST return no more than its limit, ordered
by the stable project total order `updated_at` descending with id
descending as tie-break, using keyset rather than offset traversal. It MUST
NOT return a total count or automatically follow cursors.

Each returned catalog summary MUST contain only `id`, `title`,
`description`, `created_at`, and `updated_at`. It MUST NOT contain
`settings` or `import_hash`; those remain available from the project
detail surface. Omitted query parameters MUST return only the newest 50
summaries; clients requiring an exhaustive catalog MUST follow each cursor
until null.

The cursor MUST be versioned and bound to the authenticated owner. A
malformed, oversized, non-canonical, truncated, unknown-version,
out-of-range, or cross-owner cursor MUST return 422 `VALIDATION_ERROR`
identifying `cursor` as invalid, MUST NOT enter the project store, and
MUST NOT reveal whether the embedded owner exists. Invalid zero,
over-100, fractional, or non-integer limits MUST return the same
validation code. Authentication MUST precede cursor validation so an
anonymous malformed query remains 401. A cursor is only a position marker
and MUST NOT be treated as a snapshot or authorization grant.

The project library MUST initialize from one first page, and reload or
retry MUST read only the cursorless first page. Older unique summaries
MUST append only after an explicit accessible author action; that
action's failure MUST preserve visible summaries and the saved cursor for
retry. Abort and request ownership MUST prevent stale responses from
publishing after a newer request or unmount.

#### Scenario: Default catalog is a bounded newest-first summary

- **GIVEN** an owner has more than 50 projects
- **WHEN** the project catalog is requested without query parameters
- **THEN** the newest 50 summaries are returned in descending updated-at and id order
- **AND** `next_cursor` identifies that older projects remain
- **AND** no returned item contains settings or import_hash

#### Scenario: Tie-broken order stays stable across pages

- **GIVEN** two projects share the same `updated_at`
- **WHEN** the catalog is paged across their boundary
- **THEN** the project with the greater id appears first
- **AND** neither project appears twice or is omitted

#### Scenario: Cursor traversal has no gaps or duplicates

- **GIVEN** the author follows the catalog cursors until null
- **WHEN** each page is appended by project id
- **THEN** every project appears exactly once in newest-first order
- **AND** the terminal response contains `next_cursor: null`

#### Scenario: New updates do not enter an older traversal

- **GIVEN** the author received a first page and retained its cursor
- **AND** another project is updated afterwards
- **WHEN** the author follows the retained cursor
- **THEN** the repositioned project does not displace older-page contents
- **AND** a fresh first-page read contains it

#### Scenario: Maximum pages remain bounded

- **GIVEN** an owner has more than 100 projects
- **WHEN** the catalog is requested with `limit=100`
- **THEN** exactly the newest 100 summaries are returned
- **AND** the cursor is non-null

#### Scenario: Invalid cursor scope is closed

- **GIVEN** a cursor is malformed or bound to another owner
- **WHEN** the catalog route receives it
- **THEN** the response is 422 `VALIDATION_ERROR` identifying `cursor` as invalid
- **AND** no project data or embedded-owner existence is disclosed

#### Scenario: Invalid limits do not read the catalog

- **GIVEN** `limit` is zero, greater than 100, fractional, or not an integer
- **WHEN** the catalog route receives it
- **THEN** the response is 422 `VALIDATION_ERROR`
- **AND** no catalog page is read

#### Scenario: Anonymous malformed queries stay unauthenticated

- **GIVEN** no owner session is established
- **WHEN** the catalog route receives a malformed cursor or limit
- **THEN** the response is 401 and no validation detail is produced

#### Scenario: Load older is explicit and recoverable

- **GIVEN** the project library shows a page and a non-null cursor
- **WHEN** the author activates Load older projects
- **THEN** one cursor request appends unique older summaries without clearing the page
- **BUT WHEN** that request fails
- **THEN** existing summaries and the cursor remain available for retry

#### Scenario: Reload reads only the first page

- **GIVEN** the author has loaded older pages of the catalog
- **WHEN** the library reloads or retries after a failure
- **THEN** only one cursorless first-page request is issued
- **AND** its response replaces the loaded list without automatic cursor traversal
