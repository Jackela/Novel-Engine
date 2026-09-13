# Paginate project job history

## Why

The project job-history endpoint currently loads every job, then places every
job identifier into one event query. A sufficiently long-lived project exceeds
SQLite's bind-parameter limit and turns a read-only audit request into a 500.
Smaller histories still have unbounded row, sort, payload, and browser-state
cost.

## What Changes

- Return project jobs through an opaque, project-bound keyset cursor ordered by
  `(created_at DESC, id DESC)`, with a default page of 50 and maximum of 100.
- Return `{ jobs, next_cursor }`, use `limit + 1` only to detect another page,
  and load events for no more than the returned page.
- Add the matching project/order database index through the governed migration
  channel and prove the page query does not require a temporary sort.
- Make the frontend replace state on first-page refresh, retry refresh, project
  change, and unknown-outcome audit; append only after an explicit accessible
  "Load older jobs" action.
- Preserve oldest-first events on single terminal Job responses while adding a
  list-specific contract that accurately documents newest-first list events.

## Impact

- Changes the existing `GET /api/projects/:projectId/jobs` query and response
  contracts, Studio job-history application/persistence ports, the database
  index set and migration, OpenAPI baseline, generated frontend types, and the
  Jobs inspector state/UI.
- Additive `next_cursor` is compatible with JSON clients that ignore unknown
  fields, but omitting query parameters now means the newest 50 rather than the
  complete history. Clients that require exhaustive history MUST follow cursors
  until `next_cursor` is null.
- Keeps the full Job payload in each page. Separating list summaries from job
  detail is a later change with its own compatibility review.

## Non-goals

- No offset pagination, total count, snapshot-isolation claim, automatic page
  traversal, background polling, or automatic retry.
- No Job payload reduction, job-detail route, standalone event route, retention
  policy, archival, deletion, or asynchronous worker model.
- No claim that unknown-outcome audit identifies or proves the outcome of a
  particular attempt; attempt correlation remains a separate finding.

## Validation

- Store and API tests for limits, stable ties, cursor validation and scope,
  insertion/deletion between pages, event order, ownership, and page traversal.
- A regression seeded with at least 32,767 jobs proving event lookup stays
  within one page and no longer crosses SQLite's bind limit, plus query-plan
  evidence for the composite index and absence of a temporary sort.
- Frontend contract, hook, audit, project-switch, retry-refresh, append,
  coalescing, error-preservation, and accessible control tests.
- OpenAPI snapshot and generated-type drift checks, migration gates, owning
  server/frontend full validation, strict OpenSpec, and fixed-SHA independent
  review.
