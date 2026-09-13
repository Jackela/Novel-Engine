# Design: bounded review summaries with a scoped detail read

## Baseline measurement (fixed SHA 1dd8c85f)

A temporary tracing harness (drizzle query logger around the production store,
deleted after capture) measured `listEditorialAssessments` for one project with
8 documents of ~3.5 KB chapters and increasing stored reviews:

| Stored reviews | SQL statements | Per-review follow-ups |
|---|---|---|
| 1 | 5 | 3 |
| 5 | 17 | 15 |
| 10 | 32 | 30 |
| 20 | 62 | 60 |

Confirmed fan-out (`server/src/contexts/studio/infrastructure/db/review_records.ts`):

1. One unbounded `reviews` select (no limit) plus one scoped-project read.
2. Per review — `findReviewIssues` re-reads the `reviews` row the outer loop
   already holds (pure waste).
3. Per review — `loadSnapshotDocuments` joins `snapshot_documents` with
   complete `document_revisions` rows, selecting `content_markdown` and
   `metadata_json` only to derive the `documentId -> position` map used for
   issue ordering. Measured transport: 557,120 bytes for one list read at 20
   reviews (every read re-transports the whole manuscript per stored review).
4. Per review — one `review_issues` select, and every issue's `evidence_json`
   is parsed even though the payload only forwards it.

The HTTP response then embeds every issue of every review, so response size
also grows with stored issue totals.

## Transport and cursor ownership

`GET /api/projects/:projectId/reviews` accepts optional `limit` and `cursor`
query parameters. `limit` is an integer from 1 through 100 and defaults to 50.
The strict response requires `reviews` and nullable `next_cursor`.

The cursor mirrors the jobs surface (`job_cursor.ts`): a versioned tuple
`[1, projectId, createdAtMs, reviewId]` encoded as canonical base64url, at
most 1024 characters. Decode validates exact tuple shape, version, route
project equality, a non-negative safe-integer millisecond timestamp, and a
non-empty review id of at most 128 characters. Malformed, oversized,
non-canonical, truncated, unknown-version, out-of-range, or cross-project
tokens return the same 422 `VALIDATION_ERROR` with `cursor` identified as
invalid; they do not enter persistence or reveal whether the embedded project
exists. Authentication precedes query validation, matching the jobs route.

Application and persistence ports carry a typed cursor position
(`{ createdAtMs, id }`), never the wire encoding.

## Summary shape, keyset query, and issue counts

One review summary contains only `id`, `project_id`, `snapshot_id`,
`provider`, `model`, `summary`, `issue_count`, and `created_at`; it never
contains `issues`. `issue_count` is an exact non-negative integer.

The store scopes the project first, selects only review columns ordered by
`(created_at DESC, id DESC)` with the exclusive row-value keyset predicate,
validates the 1..100 limit, reads `limit + 1`, returns at most `limit`, and
derives the next position from the last emitted row only when the lookahead
exists. One additional grouped statement
(`review_id, count(*) … where review_id in (page ids) group by review_id`)
resolves every page item's issue count, so the page costs a fixed three
statements (scope + page + counts) regardless of stored history. A page with
zero reviews skips the counts statement. The counts query is backed by the
existing `idx_review_issues_review_severity_code` prefix.

The existing `idx_reviews_project_created (project_id, created_at)` cannot
order the `id` tiebreaker, so a generated migration adds
`idx_reviews_project_created_id (project_id, created_at, id)`. Query-plan
evidence must show index-backed traversal without a temporary sort; the
migration is generated only through the declared drizzle-kit channel.

Equal-timestamp rows tie-break on `id DESC`, making the order total and the
cursor stable. Newer reviews inserted after a page remain ahead of its saved
cursor. Pagination does not claim snapshot isolation.

## Scoped detail read without revision bodies

`GET /api/projects/:projectId/reviews/:reviewId` returns the complete
assessment — including its ordered issues — for a review that belongs to the
route project; any other id is 404. The detail path reads the scoped review
row, projects `snapshot_documents` to `(document_id, position)` only (no
`document_revisions` join, no bodies, no metadata), and reads that review's
issues once. Issue ordering keeps the established `(severity, code, snapshot
position)` rule. Total cost is a fixed four statements independent of history
size, and zero snapshot-body bytes on both surfaces.

The write path (`persistReviewAssessment`) is untouched: it still builds its
ordering map from the documents it just captured in memory.

## Frontend page state, detail read, and post-run refresh

The review history state owns a newest-first summary list, a nullable
continuation cursor, and request ownership. The URL-selected lazy activation
semantics of the current Inspector histories are preserved: inactive panels
neither prefetch nor publish late outcomes, a project change aborts in-flight
requests and rejects stale responses, and failures keep a retryable error.

- **First page**: on Review-tab activation, one cursorless read initializes
  the summaries and cursor.
- **Load older**: an explicit accessible action sends `next_cursor` and
  appends unique summaries by id; duplicate activation while busy is disabled;
  failure preserves committed summaries and the cursor for retry. Keyboard
  focus rules follow the History panel: failure restores the retry control,
  terminal success moves focus to the panel heading, and a newer author-chosen
  focus target is never overridden.
- **Newest findings**: the newest summary drives one lazy detail read. An
  empty first page skips it. A detail failure is reported separately from
  history failures and is retryable. When a refreshed first page names a
  different newest review, the detail read follows it.
- **Post-run refresh**: completing a review refreshes only the cursorless
  first page (replacing summaries and cursor), then the newest detail. It
  never walks older pages and cannot be satisfied by a stale response.

## Compatibility and follow-up boundary

Clients that read issues from the list must use the detail read. Review-run
POST payloads, job evidence, snapshot lifecycle, and the deterministic review
rule set are unchanged. Export-history and project-catalog pagination remain
separate named changes and are not folded into this write set.

## Options rejected

- Keeping `issues` on bounded list items leaves per-item payload and issue
  parsing proportional to stored findings and prevents a fixed-statement page.
- A `LEFT JOIN … GROUP BY` count over the keyset query couples page projection
  with aggregation and degrades the index-backed order; two flat statements
  keep the plan strict and the count exact.
- Ordering without the `id` tiebreaker makes equal-timestamp pagination
  non-deterministic; offset pagination pays growing work on deep pages and
  drifts under concurrent inserts.
- Synthesizing the post-run summary from the job result duplicates server
  authority and cannot provide the exact issue count; the cursorless first-page
  refresh reuses one bounded read.
