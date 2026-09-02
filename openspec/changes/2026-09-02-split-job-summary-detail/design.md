# Design: cheap history summaries, explicit complete Job reads

## Two resource shapes

The project history collection returns strict `JobSummary` items with these
required wire fields:

```text
id, project_id, document_id, kind, operation, status,
provider, model, error, retry_of_job_id, created_at, updated_at
```

`request`, `result`, and `events` are absent rather than optional. Making them
optional would hide a breaking response change, preserve ambiguous client
branches, and allow large fields to leak back into the collection.

Wire types are closed and shared by OpenAPI and the frontend parser. `id`,
`project_id`, `provider`, `model`, `created_at`, and `updated_at` are strings;
`document_id`, `error`, and `retry_of_job_id` are string or null. `kind` is
`proposal`, `review`, `export`, or `import`; `operation` is `continue`,
`rewrite`, `generate`, `review`, `export`, or `import`; and `status` is
`pending`, `running`, `completed`, `failed`, or `interrupted`. Timestamps retain
the existing ISO-8601 UTC string serialization.

Complete Job payloads retain the existing required scalar fields plus parsed
request/result and events. Proposal, review, export, retry, proposal acceptance,
and SSE terminal responses remain complete Jobs. The new scoped detail GET
returns the same existing full schema; its events retain the single-Job
oldest-first order. No `latest_event` or event count is added to summaries:
status, error, and updated time already express the current list state, and the
product has no consumer for another event-derived field.

## Summary persistence path

The application/persistence port introduces `JobSummaryRecord` and
`JobSummaryPage`; it does not reuse `JobRecord`, so code requiring request,
result, or events cannot accidentally accept a summary. The page query
explicitly projects the twelve summary columns before applying the unchanged
project scope, row-value cursor, descending timestamp/id order, and
`limit + 1`. The lookahead row therefore reads summary columns only.

The list transaction still verifies the scoped project and reads one page, but
does not execute a job-events query or parse request/result/event JSON. The
existing `(project_id, created_at, id)` index remains the ordering authority;
no covering index is added because copying error and other text into an index
would increase write and storage cost without evidence of benefit.

Evidence observes actual SQL executed through the public store seam using the
test connection's supported trace/verbose hook, or an equivalent replayable
execution trace, and asserts zero `job_events` SELECT statements. Builder SQL
assertions independently prove the explicit summary projection and cannot
substitute for execution tracing.

## Scoped detail path

`GET /api/projects/:projectId/jobs/:jobId` authenticates the Owner, validates
each matched path id as 1 through 128 characters, then calls a new
application read method over the existing `findJob` port. That store path first
verifies the scoped project, then requires the job to belong to that project,
and hydrates all events in their existing oldest-first order.

The application read seam normalizes the known project-not-found and
job-not-found outcomes into one 404 `NOT_FOUND` envelope with the same stable
`Job not found.` message. Unknown project, unknown job, a job belonging to
another project, and a project outside the principal scope are therefore
indistinguishable at the response body and do not disclose cross-project
existence. Schema validation runs before the authentication pre-handler:
matched overlong parameters return 422 even without a session; validly shaped
unauthenticated requests return 401. Fastify v5 may bind a trailing empty path
segment as an empty parameter, so `minLength: 1` makes that matched request a
schema-first 422 rather than allowing authentication or lookup. Persistence
unavailability retains 503. The route has no CSRF requirement because it is
read-only.

Detail is intentionally not byte-bounded or truncated. It is an explicit read
of one durable audit object; truncating request, result, error, or event details
would break retry/audit fidelity. Current event lifecycles are small, and there
is no evidence yet for a separate event resource. If that changes, it requires
another product decision.

Summary projection removes the known unbounded nested JSON and event-row
amplification, but retained scalar strings such as `error` do not acquire a new
database length constraint. This change therefore claims a materially smaller
collection resource shape, not a mathematical response-byte ceiling. A hard
scalar-byte policy requires separate display, compatibility, and audit
decisions and is not inferred here.

## Frontend atomic migration

The frontend adds a separate `StudioJobSummary` and strict summary parser. The
Jobs page, pagination state, de-duplication, panel, and retry button use that
type. `StudioJob` and its strict complete parser remain unchanged for every
terminal workflow response. The service and frontend item-shape change land in
one candidate; a summary must never be accepted as a full Job through optional
fields.

Jobs UI already consumes only id, operation, status, provider, created time,
and error. Retry needs only the summary id/status and continues to POST directly;
its complete response is processed normally, then one fresh summary page
replaces history. Neither retry nor list rendering fetches detail first.

Unknown-outcome audit and whole-book settlement still perform exactly one fresh
summary first-page read and zero detail requests, even when `next_cursor` is
non-null. Summary success preserves the existing client-read gate semantics;
it does not identify a particular attempt. Pagination, refresh, failure
preservation, project ownership, and Load older focus behavior do not change.

No detail UI is introduced. A future explicit product request may add an
independently owned inline disclosure; it must not share pagination/audit abort
controllers or errors. A dialog is not justified for the current Jobs panel.

## Compatibility and archive ordering

Removing list fields is an intentional breaking API change. Migration guidance
is: traverse summaries, then request detail only for a specifically chosen job.
Clients must not auto-fetch detail for every page item. Deployments requiring
cross-version compatibility should first ship the detail route, then ship the
summary list in a later coordinated breaking release after clients migrate;
this repository's bundled server
and frontend are validated as one same-version release candidate.

`2026-09-02-paginate-project-jobs` introduces the active bounded-list
requirement that this change replaces. After required CI is green, pagination
MUST archive first. This change is then revalidated against the resulting
canonical requirement and archives second. Reversing the order would leave the
older active delta able to restore full events on the list.

## Options rejected

- Optional large fields or `include=detail` preserve a dual collection shape
  and invite accidental unbounded reads.
- Automatic detail prefetch recreates the list cost as N+1 requests.
- A byte threshold or truncation corrupts complete audit/retry evidence.
- An events endpoint or pagination has no current lifecycle or UI need.
- A new migration or covering index does not address the large-value projection
  defect and would add write cost.
