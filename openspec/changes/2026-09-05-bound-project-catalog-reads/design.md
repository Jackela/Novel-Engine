# Design: bounded project catalog summary pages

## Measured baseline (fixed comparison `1dd8c85f`)

The catalog read surface before this change:

| Layer | Location | Behavior |
| --- | --- | --- |
| Route | `server/src/contexts/studio/interface/http/project_routes.ts` (`GET /api/projects`) | No querystring schema; auth only; 200 = `{ projects: ProjectPayload[] }` |
| Service | `ProjectService.listProjects(principal)` | Maps every store row through `projectPayload`, parsing `settingsJson` per row |
| Store | `ProjectStorePart.findProjects(scope)` | `SELECT *` over `projects` scoped by owner, ordered `(updated_at DESC, id DESC)`, no `LIMIT` |
| Frontend | `api.projects()` → `parseProjects` → `useProjectLibraryBootstrap` → `ProjectLibraryPage` | Whole-list read on every mount/reload; strict 7-field row parse; full array render |

Per-row payload weight: `settings` is a free-form owner-editable JSON object
(unbounded via `PATCH`), `description` accepts up to 10,000 characters, and
`import_hash` is a legacy-import artifact. The library page renders only
`title`, `description`, and `updated_at`; `settings` and `import_hash` are
dead weight in the catalog read.

Reproducible large-catalog baseline (temporary vitest probe against a
hermetic `buildApp`, since deleted): 250 seeded projects, one row patched to
an ~8 KB settings blob, single unbounded read — 79,582 response bytes, 250
rows, heaviest row 8,320 bytes, typical row ~286 bytes. Cost scales linearly
with `project count × row weight`; nothing in the pipeline bounds either
axis. The store emits one SQL statement, so the defect is payload/query
shape (no bound, heavy projection), not statement count.

## Transport and cursor ownership

`GET /api/projects` accepts optional `limit` and `cursor` query parameters.
`limit` is an integer from 1 through 100 and defaults to 50 — the same
budget family as revision history and project jobs. The strict response
requires `projects` and nullable `next_cursor`; omitting query parameters
returns only the newest 50 summaries.

The HTTP interface owns the opaque cursor through the shared canonical
base64url codec already serving revision-history and job cursors
(`server/src/shared/interface/http/canonical_cursor.ts`). The token encodes
the versioned tuple `[1, ownerId, updatedAtMs, id]`. Decode validates exact
tuple shape and version, a non-negative safe-integer timestamp, and a
non-empty id of at most 128 characters, then requires the embedded owner to
equal the authenticated principal's owner scope: the catalog cursor is
owner-bound because this route has no project path parameter to bind.
Malformed, truncated, non-canonical, oversized, unknown-version,
out-of-range, or cross-owner tokens return the shared 422
`VALIDATION_ERROR` with `cursor` identified as invalid. They do not enter
persistence and do not reveal whether the embedded owner exists.

Authentication precedes schema and semantic cursor validation (the route
keeps its existing `guard` as `preHandler`): an anonymous request remains
401 even with a malformed query. Because this route reads the owner's own
catalog only and has no project-scoped 404 boundary, a syntactically valid
cursor of another owner is the only scope confusion to close, and it is
closed as 422 like every other invalid token.

Application and persistence ports carry a typed cursor position
(`{ updatedAtMs, id }`) rather than its wire encoding, matching the
revision/jobs seam. The token is a position marker, not a snapshot,
authorization grant, or stable public serialization.

## Summary shape and keyset query

One `ProjectCatalogSummary` contains only:

- `id`
- `title`
- `description`
- `created_at`
- `updated_at`

It never contains `settings` or `import_hash`. Both remain available from
`GET /api/projects/:projectId` (the shell/detail surface), and the
create/update/detail/delete contracts are unchanged. The store scopes by
owner first, selects only the five summary columns, orders by
`(updated_at DESC, id DESC)` — the stable total order already guaranteed by
the main specification — and applies the exclusive keyset predicate
`(updated_at, id) < (cursor.updated_at_ms, cursor.id)` with parameterized
row-value comparison after a cursor. It independently validates the 1..100
limit, reads `limit + 1`, returns at most `limit`, and derives the next
position from the last emitted row only when the lookahead exists.

A project updated after page one was read moves ahead of the saved cursor
and does not enter its older traversal; a fresh first-page read contains it.
Deleting a boundary project is possible between pages; the positional cursor
still reaches strictly older rows. Pagination does not claim snapshot
isolation.

The new covering index `idx_projects_owner_updated_id
(owner_id, updated_at, id)` is generated through the migration channel
(`pnpm --dir server db:generate --name paginate-project-catalog`) and
mirrors the `idx_jobs_project_created_id` precedent from
`0016_paginate-project-jobs.sql`. Without it the page query sorts the
owner's rows through a temporary B-tree; with it SQLite walks the index
range directly. Query-plan evidence in the contract test pins the index
path and the absence of a temporary sort, and pins that the statement
selects no `settings_json`.

## Frontend page state

The library bootstrap hook owns three states instead of one whole-list
read: the loaded newest-first summaries, the nullable continuation cursor,
and per-intent loading/error ownership. Initial mount and every
retry/reload read only the cursorless first page and replace the loaded
page (a reload is a fresh first-page read; older rows the author had loaded
are intentionally discarded because the reload path is the recovery
action for a failed surface). Only an explicit `Load older projects`
activation sends `next_cursor` and appends unique rows by id. A duplicate
activation while an older-page request is in flight reuses that request.

An older-page failure preserves committed rows and the cursor for retry
and surfaces the existing error message path. Session verification,
unauthenticated redirect, abort-on-unmount, and stale-response rejection
(latest request wins) keep their current semantics; an in-flight older-page
request is aborted by reload exactly like the first-page read it may race.
The API method keeps the shared credentials, error-envelope, and abort
behavior of `frontend/src/app/api.ts` and parses the page strictly
(required `next_cursor`, exact five keys per row).

The library page renders a native `Load older projects` button only while
`next_cursor` is non-null, exposes `aria-busy` while loading, and disables
duplicate activation without clearing already rendered rows. There is no
cross-owner module-global cache to budget on this surface: the hook holds
one session-scoped page list, so only deliberately loaded rows are
retained.

## Options rejected

- Keeping the unbounded read and trimming only the projection leaves row
  count unbounded; the catalog still grows without limit.
- A public full-project detail list route (settings included, paginated)
  broadens exposure to satisfy no current surface.
- Offset pagination duplicates or skips rows when updates reorder the head
  of the catalog and pays increasing work on deep pages.
- Binding the cursor to nothing (position-only token) lets one owner's
  token drive another owner's traversal; embedding and checking the owner
  scope costs one tuple field and closes it.
- A `last_updated`-only cursor breaks the existing id tie-break; the
  composite `(updated_at, id)` keyset preserves the stable total order
  exactly.
