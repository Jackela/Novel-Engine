# Tasks

## 1. Contract-first failing coverage

- [x] 1.1 Add store failures for newest-first default 50, limits 1 and 100,
      zero/over-maximum/fractional limits, nullable terminal cursor, complete
      traversal without duplicates or gaps, equal-timestamp id tie-breaking,
      concurrent newer insertion, and cross-project scope.
- [x] 1.2 Add API failures for malformed, oversized, non-canonical, truncated,
      unknown-version, unsafe timestamp, overlong id, and cross-project
      cursors; prove each returns 422 `VALIDATION_ERROR`, does not enter the
      store, and preserves auth/404 scope ordering.
- [x] 1.3 Add query-bound failures proving the summary page executes a fixed
      statement count independent of stored reviews, omits `issues` and any
      snapshot body/metadata columns, and uses an index-backed plan without a
      temporary sort; prove the detail read selects no revision bodies.
- [x] 1.4 Add detail-read failures for the scoped 404 boundary, ordered
      issues, and issue-authority separation from the list surface.

## 2. Bounded review persistence

- [x] 2.1 Add typed `ReviewPageLimit`, validated 1..100 page input,
      project-bound cursor position, summary record with exact issue count,
      and page output ports; replace the unbounded list port with the page and
      scoped-detail ports.
- [x] 2.2 Replace the per-review fan-out with the projected `limit + 1` keyset
      query plus one grouped issue-count statement; keep write-path ordering
      untouched.
- [x] 2.3 Project the detail read's ordering positions from
      `snapshot_documents` alone; remove the redundant review re-read and the
      `document_revisions` body join from read paths.
- [x] 2.4 Generate the `(project_id, created_at, id)` index migration only
      through `pnpm --dir server db:generate --name bound-review-history-keyset-index`;
      review generated SQL/metadata without hand editing either.

## 3. Bounded review API

- [x] 3.1 Add the strict query schema (`limit` default 50, cursor maximum
      1024), canonical project-bound cursor codec, required
      `{ reviews, next_cursor }` summary response, and the scoped
      `GET /reviews/:reviewId` detail route with stable error mapping.
- [x] 3.2 Prove the POST review-run flow is unchanged and its post-run client
      refresh reads exactly one cursorless first page.
- [x] 3.3 Regenerate the deliberate OpenAPI baseline and frontend API types;
      assert query bounds, 422 response, required nullable cursor, summary
      fields with `issue_count`, and the absence of `issues` on list items.

## 4. Bounded frontend review traversal

- [x] 4.1 Replace the full review list parser with summary-page parsing plus
      bounded query encoding and a strict nullable cursor; add the detail
      parser and client; preserve credentials, error envelope, and abort
      behavior.
- [x] 4.2 Refactor review history state to own summaries plus continuation
      cursor: lazy first page, explicit Load older appending unique summaries,
      failure preserving committed state, and lifecycle/request ownership
      rejecting stale project responses.
- [x] 4.3 Drive the newest assessment's findings through the lazy detail
      read, including the empty-page skip, retry, and follow-on refresh when a
      newer first page names a different newest review.
- [x] 4.4 Replace the post-run whole-list reload with one cursorless
      first-page refresh; add the accessible Load older control with busy,
      failure, and terminal states and History-panel focus rules.

## 5. Integrated evidence

- [x] 5.1 Run review run/list/detail, migration-channel, authorization,
      OpenAPI/type drift, query-bound, frontend contract/state, and
      stale/abort regressions.
- [x] 5.2 Run server type-check/lint/arch/size/full tests and gates, frontend
      lint/format/type/unit/build/check:api-types, strict OpenSpec, and record
      exact results and every skip.
- [ ] 5.3 Keep the change active until required CI is green, then merge it
      into the canonical specification and archive it.
