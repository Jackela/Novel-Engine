# Split Job summary listing from Job detail

## Why

Keyset pagination bounds the number of jobs in one response, but every listed
row still reads, parses, and transmits complete request/result JSON plus every
event. Those are the history model's highest-amplification fields, have no
stored size or count ceiling, and can exhaust a self-hosted process during an
ordinary history read even when a page contains only 50 or 100 rows.

## What Changes

- Replace each project job-list item with a strict `JobSummary` containing only
  durable scalar metadata and no request, result, or events.
- Project only summary columns in the store, including the lookahead row, and
  remove event hydration from the list path while preserving every keyset,
  cursor, ownership, and ordering rule.
- Add `GET /api/projects/:projectId/jobs/:jobId` as the project-scoped complete
  Job resource, returning the existing full payload and oldest-first events.
- Migrate the frontend Jobs history parser, state, panel, retry wiring, audit,
  and fixtures atomically to summaries while preserving complete Job parsing
  for proposal, review, export, retry, streaming, and detail responses.
- Document the removed list fields as a breaking API migration: clients needing
  one complete Job follow its id to the scoped detail resource.

## Impact

- Changes the existing jobs list store/application/HTTP/frontend item type,
  OpenAPI baseline, generated API types, and tests that used the list as an
  implicit detail endpoint.
- Adds one read route and application method over the existing scoped full-Job
  store lookup. No schema migration or new index is required.
- Same-version server and bundled frontend change together. External clients
  that consume `request`, `result`, or `events` from the list must migrate.
- Removes unbounded nested JSON/event amplification from collection reads; it
  does not claim a finite byte ceiling for every retained scalar string.

## Non-goals

- No detail UI, automatic detail prefetch, N+1 compatibility mode,
  `include=detail`, event summary/count, event endpoint or pagination, total
  count, response truncation, retention, deletion, or new database limit.
- No change to complete synchronous proposal/review/export/retry/SSE payloads,
  retry fidelity, usage aggregation, job execution, or unknown-outcome meaning.
- No attempt-correlation claim: audit still proves only that one fresh summary
  page was read after client settlement.

## Validation

- Store/query tests with sentinel large JSON and many events proving list SQL
  selects only summary columns, plus execution tracing that proves the public
  list path never queries job events.
- API tests for the strict summary shape, full detail fidelity/order,
  authentication, project/job scope, bounded parameters, and stable errors.
- Retry and terminal-response regressions proving complete Job callers still
  receive and use request/result/events.
- Frontend summary parser, pagination, audit, whole-book, retry, and no-detail-
  request tests plus OpenAPI/type drift, full local gates, browser workflows,
  strict OpenSpec, and fixed-SHA independent review.
