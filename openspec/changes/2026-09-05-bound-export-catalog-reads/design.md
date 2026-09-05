# Design: bounded export catalog pages and fixed-count snapshot assembly

## Measurement baseline

All numbers below come from the fixed baseline SHA `95a88fed` using a
temporary probe (hermetic temp SQLite, stubbed artifact gateway, monotonic
clock, statement observer through the existing `queryLogger` seam, 2 KB
chapter bodies). The probe is not part of the delivered write-set; its
scenarios were re-expressed as the bounded regressions below.

### Catalog read weight (probe A)

`listProjectArtifacts` issues a constant two statements (scoped project lookup
plus the catalog select) but returns every row with every artifact column:

| artifacts | statements | rows | JSON payload |
|---|---|---|---|
| 25 | 2 | 25 | 9,451 B |
| 50 | 2 | 50 | 18,901 B |
| 100 | 2 | 100 | 37,801 B |
| 200 | 2 | 200 | 75,601 B |

About 378 bytes per artifact with no page bound. Every Export panel activation
pays this full-history cost.

### Per-export assembly (probe B)

One export attempt on a project whose latest export snapshot no longer matches
(fresh path) issues `14 + N` statements; the reuse path issues a constant 19:

| documents | fresh total | fresh `snapshot_documents` INSERTs | reuse total | full-projection SELECTs (reuse) |
|---|---|---|---|---|
| 25 | 39 | 25 | 19 | 7 |
| 50 | 64 | 50 | 19 | 7 |
| 100 | 114 | 100 | 19 | 7 |
| 200 | 214 | 200 | 19 | 7 |

After the change, the same probe measures the fresh path at a flat
**15 total statements with exactly 1 batched `snapshot_documents` INSERT** at
every scale (25/50/100/200 documents); the reuse path is unchanged at 19
because its verification reads are the preserved durability contract.

Two confirmed findings:

1. `writeExportSnapshot` issues exactly one INSERT per captured document. Over
   a session of `E` exports with changing prose this is `E × N` statements —
   the per-export × per-document statement product. At 200 documents each
   export pays 214 statements where a batched write needs 15.
2. The reuse path holds a constant statement count but every statement that
   mentions `content_markdown` materializes all `N` bodies into JavaScript:
   the capture read, the capacity byte-scan family, the capture-time snapshot
   comparison read, the landing-time revalidation batch, and the reuse
   verification read. These are linear in the captured source per export and
   bounded by the `source_documents` (65,536) and `source_bytes` (16 MiB)
   admission limits. They are the deliberate snapshot-identity durability
   contract (capture, revalidate, reuse-verify) and stay unchanged; the
   quadratic-classified work is only the `E × N` statement loop above and the
   `E(E+1)/2` catalog curve below.

### Session catalog traffic (probe C)

The browser refreshes the complete catalog after every successful export at
100 documents (stubbed rendering; only persistence measured):

| session exports | cumulative full-catalog rows | payload | bounded first-page alternative |
|---|---|---|---|
| 50 | 1,275 | 471 KB | 2,500 rows over ≤50-row responses |
| 100 | 10,050 | 3,710 KB | 5,000 |
| 200 | 50,100 | 18,494 KB | 10,000 |

The full-catalog column is `E(E+1)/2`; the bounded column is `E × 50` and,
critically, every individual response is capped at one page instead of the
whole history.

## Transport and cursor ownership

`GET /api/projects/:projectId/exports` accepts optional `limit` and `cursor`
query parameters. `limit` is an integer from 1 through 100 and defaults to 50.
The strict response requires `exports` and nullable `next_cursor`; omitting
query parameters returns only the newest 50 artifact summaries.

The HTTP interface owns the opaque cursor through the shared canonical
base64url codec (`canonical_cursor.ts`, already proven by the jobs and
revision cursors). The token encodes a versioned tuple of the route project
id, creation epoch milliseconds, and artifact id; decoding validates exact
tuple shape and version, route identity equality, a non-negative safe-integer
timestamp, and a non-empty artifact id of at most 128 characters. Malformed,
truncated, non-canonical, oversized, unknown-version, out-of-range,
cross-project, or otherwise invalid tokens return the single 422
`VALIDATION_ERROR` with `cursor` identified as invalid, before any store
access and without revealing whether the embedded identity exists. The route
adds 422 to its documented error responses; authentication still precedes
schema and cursor validation.

Application and persistence ports carry a typed cursor position
(`{ createdAtMs, id }`), never the wire encoding. The token is a position
marker, not a snapshot or authorization grant.

## Page shape and keyset query

The artifact payload itself is already a bounded summary — identity, snapshot
binding, format, byte size, checksum, creation time, download URL — with no
file bytes. This change bounds the page, not the fields. The store scopes the
project first, selects only the catalog columns, orders by
`(created_at DESC, id DESC)`, applies the exclusive row-value predicate
`(created_at, id) < (cursor.createdAtMs, cursor.id)` after a cursor, validates
the 1..100 limit itself, reads `limit + 1`, returns at most `limit`, and
derives the next position from the last emitted row only when the lookahead
exists.

The existing `idx_exports_project_created` index cannot serve the
`(created_at, id)` tie-break, so the change ships the generated migration
`0020_paginate-export-catalog` that replaces it with
`idx_exports_project_created_id (project_id, created_at, id)` — the same
shape migration `0016` introduced for jobs. Query-plan regressions must show
index-backed traversal without a temporary sort. Because the parallel
project-catalog branch (`0020_paginate-project-catalog`, PR #473) numbers its
migration from the same baseline, a rebase conflict on the migration sequence
resolves by discarding this branch's generated artifacts and regenerating from
the merged baseline (integrator-owned).

Newer artifacts inserted after page one remain ahead of the saved cursor and
never enter its older traversal. Artifacts are append-only rows, so page
boundaries cannot be invalidated by later mutation; pagination does not claim
snapshot isolation and no deletion path exists outside project deletion.

## Fixed-count snapshot assembly

`writeExportSnapshot` currently loops `tx.insert(snapshotDocuments).values(one
row).run()` per captured document. The change assembles complete row batches
and issues one multi-row `INSERT ... VALUES (...), (...)` per at most 4,000
documents: 8 bound columns per row keep each statement below SQLite's
32,767-variable ceiling, and the per-export statement count for snapshot
creation becomes one snapshot-row insert plus `ceil(N / 4000)` batched
documents inserts — at the 65,536-document source capacity that is 17
statements instead of 65,537 — inside the same transaction with the same
generated ids, positions, and exact revision references. The batch size
mirrors the existing 500-row revalidation batching seam in
`export_source_revalidation.ts`. A statement-count regression at two document
scales proves the flat-within-batch curve. Nothing about snapshot identity,
reuse verification, source revalidation, capacity admission, artifact
publication, or recovery changes.

## Frontend page state and bounded refresh

The export history moves from an unbounded array resource to a page-owning
state: newest-first summary list, nullable continuation cursor, and request
ownership. Panel activation reads the first page. Only an explicit
`Load older exports` action sends `next_cursor` and appends unique rows by id;
a duplicate activation for the same owner and cursor coalesces. An
older-page failure preserves committed summaries and the cursor for retry.

After a successful export, the client performs one cursorless first-page
refresh — it never walks cursors. The refreshed page is prepended and
de-duplicated against already loaded immutable summaries; a loaded contiguous
older tail and its continuation cursor remain authoritative so the refresh
cannot re-read or skip the old page boundary. If a non-terminal refreshed
first page has no identity overlap with a non-empty cache (more than one page
appeared between observations), the client discards the older pages and
adopts the fresh page and cursor, exactly like the revision-history rules. The
new artifact is the newest row, so the post-export flow finds the
`export_id` from the job result on the refreshed first page (or already
loaded state) and downloads through its confined URL. Project change and
unmount abort the active request and reject late responses, preserving the
current lifecycle semantics of the lazy inspector resource.

The Export panel exposes a native `Load older exports` button only when
`next_cursor` is non-null, with busy and failure states that keep the loaded
history visible; the control follows the same keyboard-focus rules as the
History panel's Load older control (restore the retry control on failure, no
focus theft when the control simply disappears at the terminal page).

## Options rejected

- Offset pagination: deep pages pay increasing work and cannot give stable
  boundaries under new-artifact prepends.
- Keeping the full-catalog reload but compressing it: the transfer stays
  `O(E)` per export and `E(E+1)/2` per session regardless of encoding.
- Returning snapshot document counts or bodies in the catalog entry: the list
  needs no source projection; download remains the confined bytes channel.
- Bounding the per-export verification reads: capture, revalidate, and
  reuse-verify are the immutable-revision integrity contract the source issue
  explicitly preserves; they are linear per export under the source capacity
  limits, not quadratic session work.
- Caching the catalog server-side: page reads are already two indexed
  statements; a cache would add invalidation across artifact publication
  without changing the asymptotics.
