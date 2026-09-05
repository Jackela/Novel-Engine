# Bound export catalog reads and assembly

## Why

`GET /api/projects/:projectId/exports` returns every artifact a project has
ever published in one response. Measured on the fixed baseline (probe below),
one catalog read is a constant two statements but transfers the complete
history: 25 artifacts are 9.4 KB of JSON, 200 artifacts are 75.6 KB (about
378 bytes per artifact), and the row count grows without bound.

The browser reloads that complete catalog after every successful export
(`useExportDownload` refreshes the whole list to find the new artifact), so a
writing session performs a full-history transfer per export. Measured at 100
documents with stubbed rendering, the cumulative catalog traffic for a session
is the artifact-count sum: 50 exports re-read 1,275 rows (471 KB), 100 exports
re-read 10,050 rows (3.7 MB), and 200 exports re-read 50,100 rows (18.5 MB) —
the `E(E+1)/2` quadratic curve, versus `E × page` for a bounded first-page
refresh.

Export assembly also issues one INSERT statement per captured document when a
new snapshot is written: measured 25, 50, 100, and 200 documents produce
exactly 25, 50, 100, and 200 `snapshot_documents` INSERT statements per export
(14 + N total statements). Over a session of `E` exports with changing
prose this is `E × N` statements — per-export × per-document statement work
that a single multi-row insert bounds to a constant.

## What Changes

- Return the export catalog as newest-first pages through an opaque,
  project-bound keyset cursor ordered by `(created_at DESC, id DESC)`, with a
  default page of 50 and maximum of 100.
- Return `{ exports, next_cursor }`. Each artifact summary keeps its exact
  existing payload shape (identity, snapshot binding, format, byte size,
  SHA-256 checksum, creation time, download URL); the change bounds the page,
  not the artifact fields.
- Replace the post-export whole-catalog reload with one bounded cursorless
  first-page refresh that prepends and de-duplicates new summaries while
  preserving already loaded older summaries and their continuation cursor.
- Add an accessible explicit `Load older exports` action to the Export panel
  that appends one older page per activation; failures preserve committed
  summaries and the cursor for retry.
- Write every new export snapshot's document rows through fixed-size batched
  multi-row inserts (at most 4,000 documents per statement) instead of one
  statement per document, keeping the exact snapshot revision sets and all
  publication/recovery semantics unchanged.
- Add the keyset index `(project_id, created_at, id)` on `exports` through a
  generated migration that replaces the now-insufficient
  `(project_id, created_at)` index.

## Impact

- Changes `GET /api/projects/:projectId/exports` query and response contracts,
  the export application/persistence ports, the OpenAPI baseline, generated
  frontend types, API parsing, Studio export history state, and the Export
  panel.
- The list contract is intentionally breaking for clients that treated the
  response as the complete history. Such clients must follow `next_cursor`
  until null; download URLs, artifact payloads, creation, retry, publication,
  recovery, and deletion semantics do not change.
- The schema change ships as one generated index migration; no data
  transformation is required.
- No new dependency, environment variable, or route path is introduced.

## Non-goals

- No offset pagination, total count, automatic cursor traversal, retention or
  deletion policy, or new artifact-detail endpoint.
- No change to snapshot identity verification, source revalidation, capacity
  admission, artifact publication/recovery, or download confinement. The
  measured per-export full-projection verification passes (capture, revalidate,
  reuse-verify) stay exactly as they are; they are linear in the captured
  source and bounded by the existing source capacity limits.
- No pagination redesign for editorial reviews or project shells; each remains
  a separate named change.

## Validation

- Store/API traversal tests for default/minimum/maximum limits, stable
  `(created_at DESC, id DESC)` order, nullable terminal cursor, complete
  traversal without duplicates or gaps, ownership, and malformed, oversized,
  non-canonical, unknown-version, cross-project, and cross-document cursors
  returning 422 `VALIDATION_ERROR` without entering the store.
- Query-plan evidence that the catalog page uses the new keyset index without
  a temporary sort, and statement-count evidence that a fresh snapshot write
  issues one batched `snapshot_documents` insert regardless of document count.
- Snapshot identity, revalidation, capacity, publication, and recovery
  regressions proving the exact revision sets and outcome semantics are
  unchanged.
- Frontend contract tests for first-page initialization, explicit older-page
  append with de-duplication, bounded post-export refresh that does not walk
  cursors, failure recovery, and the accessible Load older control.
- OpenAPI and generated-type drift checks, migration-channel gate, server and
  frontend full test suites, and strict OpenSpec validation.
