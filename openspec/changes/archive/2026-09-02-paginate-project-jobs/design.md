# Design: bounded keyset traversal for project jobs

## Transport and layer ownership

`GET /api/projects/:projectId/jobs` accepts optional `limit` and `cursor` query
parameters. `limit` is an integer from 1 through 100 and defaults to 50. The
response is a strict object whose required fields are `jobs` and nullable
`next_cursor`.

The HTTP interface owns the opaque token. It accepts at most 1024 base64url
characters and decodes a versioned JSON payload containing the project id,
millisecond timestamp, and job id into a typed application cursor, then encodes
the next typed position on the way out.
The application and persistence ports do not know the wire representation.
Decode accepts only the documented base64url alphabet and a bounded token
length, requires a canonical re-encoding and exact known fields, validates the
version, non-empty ids and safe-integer timestamp, and requires the token's
project id to equal the route project. The typed port carries `createdAtMs` as a
non-negative safe integer and never constructs a JavaScript `Date` from cursor
input; the job id is non-empty and at most 128 characters. Malformed,
truncated, unknown-version, out-of-range, or cross-project tokens all return
the same 422 `VALIDATION_ERROR` shape with the cursor identified as invalid;
none reveals whether another project exists.

The token is a position marker, not a database snapshot, authorization grant,
or durable bookmark format. Its structure remains an implementation detail and
clients treat it as opaque.

## Keyset query and page boundary

The store verifies project ownership through the existing scope before reading
jobs. It orders by `(created_at DESC, id DESC)` and, after a cursor, applies one
parameterized SQLite row-value predicate:

```text
(created_at, id) < (cursor.createdAtMs, cursor.id)
```

The row-value form lets SQLite constrain the composite-index range rather than
scanning every newer entry in a deep page. The store independently validates
that `limit` is an integer from 1 through 100 before calculating `limit + 1`,
even when called outside HTTP. The extra row determines whether another page
exists but is not returned and is not included in the event lookup. When
another page exists, the next position is the last row actually returned;
otherwise `next_cursor` is null.

Ownership lookup, lookahead job selection, and returned-page event hydration
run in one store transaction/read snapshot. Events are queried for at most
`limit` job ids using `ORDER BY job_id DESC, sequence DESC`, which can scan the
existing `(job_id, sequence)` unique index backwards while keeping every job's
events newest-first. The lookahead job never participates in event hydration.

Because the predicate is positional, deleting the boundary row after page one
does not block page two. A newer job inserted after page one stays before the
saved position: it appears on a fresh first page and is not injected into the
older traversal. Keyset traversal intentionally does not promise a frozen
snapshot of concurrent mutations.

## Index and migration authority

The jobs table replaces `idx_jobs_project_id` with an index whose key prefix is
`project_id` followed by `created_at` and `id`. The composite leftmost prefix
serves project-only equality lookups, while SQLite can scan the full ascending
index backwards for the required descending order. The migration is generated with the
repository's `db:generate --name <semantic-kebab>` workflow; generated metadata
is never hand-edited. Query-plan evidence must show a composite-index tuple
range rather than project equality alone and no temporary B-tree for job or
event ordering. The generated SQL must create the composite index and drop the
redundant single-column index; SQL and metadata are reviewed, never hand-edited.

## Frontend state transitions

The API client parses both required response fields and appends encoded query
parameters without changing the shared credentials, CSRF, abort, or error
envelope behavior. The Studio jobs hook owns both the visible jobs and the next
cursor:

- first load, Refresh, visible-Jobs project switch, accepted proposal refresh, retry
  completion refresh, and unknown-outcome audit request the first page, replace
  jobs, and replace/reset the cursor;
- only the explicit `Load older jobs` action sends the saved cursor and appends
  a successful page, de-duplicating by job id defensively;
- an older-page failure preserves the current jobs and cursor so the author can
  retry; duplicate load-more activation is coalesced;
- abort/epoch ownership prevents a late page from a previous project or older
  request from mutating current state.

Only duplicate requests for the same project and same older-page cursor may
coalesce. Any first-page replacement intent invalidates an older-page request
and starts its own cursorless request; a late older page cannot append or
replace its cursor. This applies to Refresh, accepted-proposal refresh, retry
completion, project change while Jobs is visible, and audit. Project change
always clears old jobs and cursor immediately. When Jobs is hidden it stays
empty until opened; when Jobs remains visible it starts exactly one new-project
first-page request.

Within the same project, a first-page result replaces jobs and cursor only
after it succeeds. Failure preserves the last committed jobs and cursor and
surfaces a retryable error; audit additionally enters its existing failed gate.
Project switching is the ownership exception: old-project state is cleared
immediately and is never restored when the new project's first read fails.

Unknown-outcome audit performs exactly one fresh first-page read and never
coalesces with a request begun before client settlement. A successful read
settles the existing client audit gate and preserves its warning semantics even
when `next_cursor` is non-null. It does not auto-traverse history and does not
claim correlation with the unknown attempt. Loading older jobs never changes
audit status.

The Jobs panel presents an accessible, independently named load-older control
only when another page exists. Its busy state prevents duplicate activation;
Refresh and Load older remain distinct actions. When a keyboard-triggered load
reaches the end and removes that focused control, focus moves to the stable
Refresh jobs control. Failure keeps the load-older control focused and
available for retry. Existing jobs are never disturbed by either focus change.

## Compatibility and follow-up boundary

Existing small histories retain their visible order and full payload. Clients
that assumed an omitted query returned every job must migrate to cursor
traversal. No `total_count` is provided because computing it restores work
proportional to total history and is not needed by the product flow.

Full request, result, and event bodies can still make a page large. A later
OpenSpec change will define a compact `JobSummary` list and a scoped
`GET /api/projects/:projectId/jobs/:jobId` detail resource. It must separately
review retry, audit, UI, and external-client compatibility.

## Options rejected

- Offset pagination permits duplicates/skips under concurrent inserts and pays
  increasing scan cost for old pages.
- Returning a total count adds an unbounded aggregate to a bounded read.
- Automatically walking all pages recreates the failure in the client and does
  not strengthen unknown-outcome evidence.
- Combining summary/detail splitting here obscures which contract change causes
  failures and broadens the migration surface.
