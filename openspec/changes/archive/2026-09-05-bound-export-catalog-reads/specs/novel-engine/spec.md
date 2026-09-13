## ADDED Requirements

### Requirement: Bounded export catalog traversal

`GET /api/projects/:projectId/exports` MUST return a strict object containing
required `exports` and `next_cursor`, where `next_cursor` is an opaque string
or null. It MUST accept an optional integer `limit` from 1 through 100,
defaulting to 50, and an optional opaque cursor of at most 1024 canonical
base64url characters. Each page MUST return no more than its limit, ordered by
`(created_at DESC, id DESC)` using stable keyset rather than offset traversal,
and MUST NOT return a total count or automatically follow cursors. Every
returned summary MUST keep the exact artifact catalog fields — identity,
project and snapshot binding, format, byte size, SHA-256 checksum, creation
time, and confined download URL — and MUST NOT carry artifact bytes.

The cursor MUST be versioned and bound to the route project. A malformed,
oversized, non-canonical, truncated, unknown-version, out-of-range,
cross-project, or otherwise invalid cursor MUST return 422
`VALIDATION_ERROR` identifying `cursor` as invalid, MUST NOT enter the export
store, and MUST NOT reveal whether the embedded scope exists. Invalid zero,
over-100, fractional, or non-integer limits MUST return the same validation
code. A cursor is only a position marker and MUST NOT be treated as a
snapshot, authorization grant, or public durable encoding.

The Studio MUST initialize the Export panel from one first page and append
older unique summaries only after an explicit accessible author action. After
a successful export it MUST refresh at most the cursorless first page, MUST
prepend and de-duplicate new summaries while preserving any loaded contiguous
older summaries and their continuation cursor, and MUST NOT traverse the
complete history. Older-page failure and refresh failure MUST preserve
committed summaries and the saved cursor for retry. Project, abort, and
request ownership MUST prevent stale responses from publishing into another
project.

Writing a new export snapshot MUST persist its complete document set through
fixed-size batched inserts whose statement count grows at most once per
4,000 captured documents, while preserving the exact snapshot revision sets
and all artifact publication and recovery semantics.

#### Scenario: Default catalog is a bounded newest-first page

- **GIVEN** a project has more than 50 export artifacts
- **WHEN** its export catalog is requested without query parameters
- **THEN** the newest 50 summaries are returned in descending
  created-at-and-id order
- **AND** `next_cursor` identifies that older history remains
- **AND** no returned item carries artifact bytes

#### Scenario: Cursor traversal has no gaps or duplicates

- **GIVEN** the author follows one project's export cursors until null
- **WHEN** each page is appended by artifact id
- **THEN** every artifact appears exactly once in newest-first order
- **AND** the terminal response contains `next_cursor: null`

#### Scenario: New exports do not enter an older traversal

- **GIVEN** the author received a catalog page and retained its cursor
- **AND** another export completes afterwards
- **WHEN** the author follows the retained cursor
- **THEN** the newer artifact is not injected into the older page
- **AND** a fresh first-page read contains it

#### Scenario: Invalid cursor scope is closed

- **GIVEN** a cursor is malformed or bound to another project
- **WHEN** the export catalog route receives it
- **THEN** the response is 422 `VALIDATION_ERROR` identifying `cursor` as invalid
- **AND** no artifact data or embedded-scope existence is disclosed

#### Scenario: Invalid limits do not read the catalog

- **GIVEN** `limit` is zero, greater than 100, fractional, or not an integer
- **WHEN** the export catalog route receives it
- **THEN** the response is 422 `VALIDATION_ERROR`
- **AND** no catalog page is read

#### Scenario: Repeated exports perform bounded refreshes

- **GIVEN** a project has more than one page of export history
- **WHEN** repeated exports succeed
- **THEN** each completion triggers at most one cursorless first-page refresh
- **AND** no completion automatically requests an older page
- **AND** already loaded older summaries and their continuation remain usable

#### Scenario: Load older exports is explicit and recoverable

- **GIVEN** the Export panel shows a page and a non-null cursor
- **WHEN** the author activates Load older exports
- **THEN** one cursor request appends unique older summaries without clearing the page
- **BUT WHEN** that request fails
- **THEN** existing summaries and the cursor remain available for retry
- **AND** keyboard focus returns to the retryable control or stays with the author's newer focus choice

#### Scenario: Snapshot assembly statements grow by fixed batches

- **GIVEN** two projects whose export sources capture different document counts
  within one insert batch
- **WHEN** each writes a fresh export snapshot
- **THEN** each publication issues the same number of snapshot-document insert
  statements regardless of the captured document count within that batch
- **AND** every captured document/revision pair, position, and presentation
  field is persisted exactly as before
