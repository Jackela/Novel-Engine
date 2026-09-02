# Design: bounded revision summaries with exact persisted counts

## Transport and cursor ownership

`GET /api/projects/:projectId/documents/:documentId/revisions` accepts optional
`limit` and `cursor` query parameters. `limit` is an integer from 1 through 100
and defaults to 50. The strict response requires `revisions` and nullable
`next_cursor`; omitting query parameters returns only the newest 50 summaries.

The HTTP interface owns the opaque cursor. It accepts at most 1024 canonical
base64url characters and encodes a versioned tuple containing the route project
id, route document id, revision number, and revision id. Decode validates exact
tuple shape and version, route identity equality, revision number as a positive
safe integer, and a non-empty revision id of at most 128 characters. Malformed,
truncated, non-canonical, oversized, unknown-version, out-of-range,
cross-project, or cross-document tokens return the same 422 `VALIDATION_ERROR`
with `cursor` identified as invalid. They do not enter persistence or reveal
whether the embedded identity exists.

Application and persistence ports carry a typed cursor position rather than its
wire encoding. The token is a position marker, not a snapshot, authorization
grant, or stable public serialization.

## Summary shape and keyset query

One `RevisionSummary` contains only:

- `id`
- `document_id`
- `parent_revision_id`
- `revision_number`
- `source`
- `word_count`
- `created_at`

It never contains `content_markdown` or `metadata`. The store scopes the project
and document first, selects only these columns, orders by
`(revision_number DESC, id DESC)`, and applies the exclusive keyset predicate
after a cursor. It independently validates the 1..100 limit, reads `limit + 1`,
returns at most `limit`, and derives the next position from the last emitted
row only when the lookahead exists. The existing unique
`(document_id, revision_number)` index supports the descending document range;
the id is a total-order guard even though valid revision numbers are unique.
Query-plan evidence must show index-backed document/range traversal without a
temporary sort. No new pagination index is expected unless that evidence
disproves the existing index.

Newer revisions inserted after page one remain ahead of the saved cursor and do
not enter its older traversal. Deleting the boundary revision is not an ordinary
product operation, but a direct-store regression proves the positional cursor
still reaches older rows if cleanup or test fixtures remove it. Pagination does
not claim snapshot isolation.

## Exact word-count authority and upgrade

`word_count` remains part of History because it is the panel's only size signal.
Computing it in the summary query would require selecting every body and would
preserve the defect. Approximating it in SQLite would change the existing
Unicode-aware `/[\p{L}\p{N}_'-]+/gu` semantics. The count therefore becomes an
immutable stored projection of the immutable body.

The pure counter moves to a Studio domain utility so both payload builders and
infrastructure writes use one definition. The sole revision insertion helper
computes and stores a non-negative exact count in the same transaction as the
revision. Full document/revision payloads consume the stored value rather than
rescanning text.

The Drizzle schema adds nullable `word_count`; the migration is generated with
`pnpm --dir server db:generate --name persist-revision-word-count`, and neither
its SQL nor metadata is hand-edited. Null is an upgrade sentinel only. After
schema migration and the existing pre-migration backup, a context-owned
pre-serve reconciler repeatedly selects at most 256 null rows with only
`id, content_markdown`, computes exact counts, and updates that batch in one
transaction. Committed batches are restart-safe progress; a crash resumes from
remaining null rows. The server fails before traffic if reading, counting, or
updating fails, and verifies no null remains before export reconciliation and
job recovery. Fresh writes never create null. Application/store boundaries
reject a null or negative count rather than publishing false evidence.

This one-time upgrade may read every historic body, but memory is bounded by one
batch and future list/autosave reads never select bodies. Backup authority,
revision contents, metadata, parentage, numbering, and timestamps are unchanged.

## Exact restore without list bodies

The restore request continues to name the revision id and the current base
revision id. `RevisionService.replayRevision` retains its scoped exact
`findRevision(projectId, documentId, revisionId)` read, including the selected
body and metadata, then creates a new `restore` revision through the existing
conflict-checked path. List cursors and cached summaries are never restoration
authority. A revision not belonging to the route document remains 404, and a
stale base remains 409 with no new revision.

## Frontend page state and autosave refresh

Each cached owner stores a newest-first summary list, nullable continuation
cursor, and request ownership. Initial document activation reads the first page.
Only an explicit `Load older revisions` action sends `next_cursor` and appends
unique rows by id. A duplicate request for the same owner and cursor coalesces;
other overlapping intents do not.

After autosave, proposal acceptance, or restore creates a known revision, the
existing bounded first-page endpoint is refreshed; no cursor chain is walked.
On success its new summaries are prepended/de-duplicated against already loaded
immutable summaries. If an owner already held a contiguous loaded tail, its
existing tail and continuation cursor remain authoritative: this prevents a
new first-page cursor from re-reading or skipping the old page boundary. An
empty owner adopts the response cursor. A terminal loaded history remains
terminal after new rows are prepended because all older rows were already held.

A first-page refresh failure preserves committed summaries and the continuation
cursor while surfacing the existing revision error. An older-page failure does
the same, leaving Load older available. A document/project change immediately
publishes only that owner's cached state (or empty state), aborts the previous
owner's active request, and increments request ownership. Late responses cannot
publish into a new owner or supersede a newer request. These rules preserve the
current lifecycle epoch, abort, and stale-response semantics.

## Bounded cross-owner cache and accessible traversal

The module-global cache and request-version registry share an eight-owner LRU
bound keyed by `(projectId, documentId)`. Reading or successfully publishing an
owner makes it most recent. Inserting a ninth owner evicts the least-recently
used inactive owner and deletes its request-version entry; the active owner is
never evicted. Eviction affects only browser acceleration—a later visit performs
a fresh first-page read. In-flight ownership stays hook-local and is aborted on
owner transition/unmount, so eviction cannot revive a stale request.

The History panel shows a native button named `Load older revisions` only when
`next_cursor` is non-null. It exposes a busy state and disables duplicate
activation while retaining the already displayed history. On failure, focus
stays on the retryable button. When a keyboard-triggered terminal page removes
that control, focus moves to the stable History heading. Screen-reader-visible
status distinguishes loading from the end of history; no automatic infinite
scroll is introduced.

## Compatibility and follow-up boundary

Clients that depended on full bodies or metadata in the list must adapt; those
fields are deliberately absent rather than nullable. Clients needing exhaustive
summaries must follow cursors until null. Save and restore success payloads do
not change, and exact restore remains available from every loaded summary.

Project-shell payload splitting, review summary/detail pagination, project
catalog pagination, and export catalog pagination are separate changes. They
must not be folded into this write set.

## Options rejected

- Keeping dynamic `word_count` preserves full-body selection and repeated
  Unicode scans; replacing it with byte/character length would publish a
  different fact.
- Removing `word_count` is smaller technically but regresses the current History
  signal and shifts the contract merely to avoid migration work.
- Offset pagination permits gaps or duplicates as autosave prepends revisions
  and pays increasing work on deep pages.
- Automatically following every cursor recreates unbounded browser/network
  work.
- Returning revision bodies from a new public detail endpoint is unnecessary
  for restore and broadens data exposure; a future preview feature must specify
  its own bounded contract.
