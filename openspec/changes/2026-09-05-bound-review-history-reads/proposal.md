# Bound Review history reads

## Why

`GET /api/projects/:projectId/reviews` returns every stored assessment for a
project in one response, and each item carries its complete ordered issue list.
Serving that list executes per-review follow-up queries: for every assessment
the store re-reads the review row it already holds, joins `snapshot_documents`
with complete `document_revisions` rows (bodies and metadata included) only to
recover issue-order positions, and queries `review_issues` once more. A
baseline measurement on the pre-change store (fixed SHA `1dd8c85f`) counted
`2 + 3N` SQL statements for `N` stored reviews — 5, 17, 32, and 62 statements
at 1, 5, 10, and 20 reviews — and one list read against 20 reviews of an
8-document project with ~3.5 KB chapters transported 557,120 bytes of snapshot
bodies and metadata that no client consumes. Both statement count and payload
grow without bound as review history accumulates, while the Review panel needs
only the newest assessment's findings plus a bounded history list.

## What Changes

- Return review history as newest-first summary pages through an opaque,
  project-bound keyset cursor ordered by `(created_at DESC, id DESC)`, with a
  default page of 50 and maximum of 100.
- Return `{ reviews, next_cursor }`. Review summaries retain identity,
  snapshot binding, provider, model, fixed summary text, exact issue count,
  and creation time, but exclude the `issues` array.
- Add one scoped detail read, `GET /api/projects/:projectId/reviews/:reviewId`,
  returning the complete assessment with its ordered issues. The list surface
  never serves as issue authority.
- Eliminate the per-review query fan-out: a summary page reads the project
  scope, the bounded keyset page, and one grouped issue-count statement;
  the detail read resolves its issue order from stored snapshot positions
  without selecting revision bodies or metadata.
- Keep the Review panel's lazy URL-selected activation, abort, stale-response,
  and failure/retry semantics; initialize it from one bounded first page, add
  an explicit accessible "Load older reviews" action, and load the newest
  assessment's findings through the detail read.
- After a completed review run, refresh only the cursorless first page and the
  newest assessment's detail; never re-traverse older pages.

## Impact

- Changes `GET /api/projects/:projectId/reviews` query and response contracts,
  adds `GET /api/projects/:projectId/reviews/:reviewId`, changes the review
  application/persistence ports, the OpenAPI baseline, generated frontend
  types, frontend review API parsing, review history state, and the Review
  panel.
- The list contract is intentionally breaking for clients that read issues
  from the list. Such clients must use the scoped detail read. No other client
  exists today.
- Persistence adds one generated index migration backing the keyset order
  `(project_id, created_at, id)`; review rows, issues, snapshots, and jobs are
  unchanged.
- No dependency, environment variable, review-run request/response, job
  payload, or snapshot lifecycle change is required.

## Non-goals

- No offset pagination, total count, automatic traversal, or review deletion.
- No pagination or payload redesign for export history or project catalogs;
  each remains a named later change.
- No change to review evaluation, snapshot capture, issue ordering vocabulary,
  provider provenance, or job evidence.
- No per-review issue pagination: one assessment's issue list is bounded by
  the deterministic rule set and is served whole by the detail read.

## Validation

- Store/API traversal tests for default/minimum/maximum limits, stable order,
  nullable terminal cursor, complete traversal without duplicates or gaps,
  concurrent newer inserts, equal-timestamp tie-breaking, ownership, and
  malformed/cross-project cursors.
- Query-bound tests proving the summary page executes a fixed statement count
  independent of stored review count, selects no snapshot bodies or metadata,
  and uses an index-backed plan without a temporary sort.
- Frontend contract tests for first-page initialization, explicit older-page
  append, detail loading of the newest assessment, post-run bounded refresh,
  error preservation, retry, and stale/aborted response rejection.
- OpenAPI and generated-type drift, migration-channel, server/frontend full
  tests, strict OpenSpec, and fixed-SHA evidence.
