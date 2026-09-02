## ADDED Requirements

### Requirement: Bounded document revision-history traversal

`GET /api/projects/:projectId/documents/:documentId/revisions` MUST return a
strict object containing required `revisions` and `next_cursor`, where
`next_cursor` is an opaque string or null. It MUST accept an optional integer
`limit` from 1 through 100, defaulting to 50, and an optional opaque cursor of at
most 1024 canonical base64url characters. Each page MUST return no more than its
limit, ordered by `(revision_number DESC, id DESC)`, using stable keyset rather
than offset traversal. It MUST NOT return a total count or automatically follow
cursors.

Each returned revision summary MUST contain only `id`, `document_id`,
`parent_revision_id`, `revision_number`, closed server-assigned `source`, exact
non-negative `word_count`, and `created_at`. It MUST NOT contain
`content_markdown` or `metadata`. Omitted query parameters now return only the
newest 50 summaries; clients requiring exhaustive summary history MUST follow
each cursor until null.

The cursor MUST be versioned and bound to both route project and route document.
A malformed, oversized, non-canonical, truncated, unknown-version,
out-of-range, cross-project, or cross-document cursor MUST return 422
`VALIDATION_ERROR` identifying `cursor` as invalid, MUST NOT enter the history
store, and MUST NOT reveal whether the embedded scope exists. Invalid zero,
over-100, fractional, or non-integer limits MUST return the same validation
code. A cursor is only a position marker and MUST NOT be treated as a snapshot,
authorization grant, or public durable encoding.

The Studio MUST initialize History from one first page and append older unique
summaries only after an explicit accessible author action. Older-page failure
MUST preserve visible summaries and the saved cursor for retry. Project,
document, abort, and request ownership MUST prevent stale responses from
publishing into another owner. The shared cross-owner revision cache MUST retain
at most eight project/document owners while its active working set is no larger
than eight, and MUST evict the least-recently-used inactive owner without
evicting an active owner. If more than eight owners are simultaneously active,
it MAY temporarily retain only that unavoidable active working set and MUST
converge to at most eight as owners deactivate. Coalesced requests MUST notify
every still-mounted subscriber, and an initiating subscriber's unmount MUST NOT
suppress the outcome for a surviving subscriber.

#### Scenario: Default history is a bounded newest-first summary

- **GIVEN** a document has more than 50 immutable revisions
- **WHEN** its revision history is requested without query parameters
- **THEN** the newest 50 summaries are returned in descending number-and-id order
- **AND** `next_cursor` identifies that older history remains
- **AND** no returned item contains revision content or metadata

#### Scenario: Maximum pages remain bounded

- **GIVEN** a document has more than 100 revisions
- **WHEN** history is requested with `limit=100`
- **THEN** exactly the newest 100 summaries are returned
- **AND** the cursor is non-null

#### Scenario: Cursor traversal has no gaps or duplicates

- **GIVEN** the author follows one document's cursors until null
- **WHEN** each page is appended by revision id
- **THEN** every revision appears exactly once in newest-first order
- **AND** the terminal response contains `next_cursor: null`

#### Scenario: New saves do not enter an older traversal

- **GIVEN** the author received a first page and retained its cursor
- **AND** autosave creates a newer revision
- **WHEN** the author follows the retained cursor
- **THEN** the new revision is not injected into the older page
- **AND** a fresh first-page read contains it

#### Scenario: A deleted boundary does not block older history

- **GIVEN** a page cursor records its last returned position
- **AND** that boundary row is later absent
- **WHEN** the saved cursor is followed
- **THEN** older revisions are still returned from the recorded position

#### Scenario: Invalid cursor scope is closed

- **GIVEN** a cursor is malformed or bound to another project or document
- **WHEN** the revision-history route receives it
- **THEN** the response is 422 `VALIDATION_ERROR` identifying `cursor` as invalid
- **AND** no revision data or embedded-scope existence is disclosed

#### Scenario: Invalid limits do not read history

- **GIVEN** `limit` is zero, greater than 100, fractional, or not an integer
- **WHEN** the revision-history route receives it
- **THEN** the response is 422 `VALIDATION_ERROR`
- **AND** no history page is read

#### Scenario: Load older is explicit and recoverable

- **GIVEN** the History panel shows a page and a non-null cursor
- **WHEN** the author activates Load older revisions
- **THEN** one cursor request appends unique older summaries without clearing the page
- **BUT WHEN** that request fails
- **THEN** existing summaries and the cursor remain available for retry

#### Scenario: Terminal keyboard focus stays in History

- **GIVEN** keyboard focus is on Load older revisions
- **WHEN** the terminal page succeeds and removes that control
- **THEN** focus moves to the stable History heading
- **BUT WHEN** loading fails
- **THEN** focus stays on the retryable Load older revisions control

#### Scenario: Cross-owner cache is bounded

- **GIVEN** the author has visited revision history for eight inactive documents
- **WHEN** a ninth project/document owner enters the shared cache
- **THEN** the least-recently-used inactive owner is evicted
- **AND** the active owner remains available
- **AND** revisiting an evicted owner starts a fresh first-page read

#### Scenario: Active working set converges to the cache budget

- **GIVEN** more than eight project/document owners are simultaneously active
- **WHEN** inactive owners exist or active owners deactivate
- **THEN** inactive owners are evicted before any active owner
- **AND** the retained owner count converges to at most eight when the active set permits it

### Requirement: Exact immutable revision word counts

Every accepted revision MUST retain the exact non-negative word count of its
immutable Markdown body using the established Unicode-aware counting semantics.
Every document and revision-summary response MUST report that retained count
without changing the underlying body, and an upgrade MUST populate exact counts
for all earlier revisions before the server accepts traffic. Interrupted upgrade
work MUST resume without corrupting revisions or publishing placeholder counts;
an unrecoverable count migration failure MUST fail startup. Every full Document,
full Revision, and RevisionSummary projection MUST reject a null, negative,
non-integer, or unsafe stored count with the same typed internal invariant
failure. That failure MUST NOT expose storage details through a new public error
code or envelope.

#### Scenario: New revisions retain their exact count

- **GIVEN** Markdown containing letters, numbers, Chinese text, apostrophes, and hyphens
- **WHEN** a save, import, accepted proposal, or restore creates a revision
- **THEN** its retained word count equals the established Unicode-aware result
- **AND** the count and revision commit together

#### Scenario: Existing histories are backfilled before serving

- **GIVEN** an earlier database whose revisions have no retained word count
- **WHEN** the upgraded release starts successfully
- **THEN** every existing revision has its exact count before requests are accepted
- **AND** content, metadata, identity, parentage, numbering, source, and timestamps are unchanged

#### Scenario: Interrupted backfill resumes safely

- **GIVEN** some earlier revision counts were committed before startup stopped
- **WHEN** startup runs again
- **THEN** remaining revisions are populated without rewriting completed counts
- **AND** no placeholder or negative count is exposed

### Requirement: Bounded revision refresh and exact restore

After autosave, proposal acceptance, or restore creates a revision, the Studio
MUST refresh at most the cursorless first summary page and MUST NOT traverse the
complete history. The successful first page MUST prepend and de-duplicate new
summaries while preserving any contiguous older summaries and their continuation
cursor. A non-terminal first page with no identity overlap MUST replace rather
than splice across an unknown cache gap. Refresh ownership MUST distinguish the
revision created by each mutation so an older response cannot satisfy a newer
mutation. A failed refresh MUST preserve committed history state and expose the
existing revision error. A successful older-page request MUST NOT clear that
first-page error; only a successful request of the same history intent may
clear the corresponding error.

Restoring a listed revision MUST resolve that exact scoped revision's complete
body and metadata on the server, MUST create a new revision with source
`restore` through the existing base-revision conflict check, and MUST NOT treat
the summary, cache, or cursor as content authority.

#### Scenario: Repeated autosave performs bounded refreshes

- **GIVEN** a document has more than one page of revision history
- **WHEN** repeated autosaves succeed
- **THEN** each save triggers at most one cursorless first-page history read
- **AND** no save automatically requests an older page
- **AND** already loaded older summaries and their continuation remain usable

#### Scenario: A stale first-page response cannot overwrite current history

- **GIVEN** a history refresh is in flight for one project/document owner
- **WHEN** the author changes document or a newer refresh takes ownership
- **THEN** the stale response cannot publish summaries or cursor state

#### Scenario: Older success does not hide a refresh failure

- **GIVEN** a first-page refresh fails while an older-page action is queued
- **WHEN** the older-page request later succeeds
- **THEN** its summaries may append to the retained contiguous tail
- **BUT** the failed first-page revision error remains visible until a first-page request succeeds

#### Scenario: Summary-only restore remains exact

- **GIVEN** the browser holds only a summary for historic revision A
- **WHEN** the author restores A against the current base revision
- **THEN** the server reads A's exact body and metadata from immutable authority
- **AND** creates a new `restore` revision containing that body and restoration metadata

#### Scenario: Restore conflicts preserve both histories

- **GIVEN** another save advances the document after the restore base was chosen
- **WHEN** the author submits the restore
- **THEN** the existing 409 revision-conflict response is returned
- **AND** neither the selected historic revision nor the newer current revision is changed
