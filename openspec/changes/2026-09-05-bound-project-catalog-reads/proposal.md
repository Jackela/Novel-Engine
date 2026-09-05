# Bound project catalog reads

## Why

`GET /api/projects` returns every project of the owner in one response with
no bound. Each catalog row is a full Project payload: it parses and includes
the free-form `settings` JSON (owner-editable, unbounded) plus the up to
10,000-character `description` and `import_hash`, none of which the project
library surface renders. The store read is a whole-table `SELECT *` ordered
by `(updated_at DESC, id DESC)` with no `LIMIT`.

A measured baseline (worktree evidence, 250 seeded projects, one row carrying
an ~8 KB settings blob) produced a single 79,582-byte response; the heaviest
row serialized to 8,320 bytes. Catalog cost therefore grows linearly with
project count times per-row settings/description weight, and the frontend
re-reads that complete list on every library mount and reload.

## What Changes

- Return the project catalog as newest-first summary pages through an opaque,
  owner-bound keyset cursor ordered by the established
  `(updated_at DESC, id DESC)` total order, with a default page of 50 and
  maximum of 100.
- Return `{ projects, next_cursor }`, where `next_cursor` is an explicit
  nullable string. Each catalog summary contains only `id`, `title`,
  `description`, `created_at`, and `updated_at`; `settings` and `import_hash`
  leave the list and remain available from the project shell/detail surface.
- Reject invalid cursors and limits with the shared 422 `VALIDATION_ERROR`
  envelope before persistence, without disclosing whether the embedded owner
  scope exists.
- Add the covering `(owner_id, updated_at, id)` index through a generated
  migration so the keyset page is index-backed without a temporary sort.
- Give the project library a bounded first page with an accessible explicit
  "Load older projects" action; reload and retry still read only the first
  page, older rows append uniquely by id, and failures preserve committed
  rows plus the continuation cursor for retry.

## Impact

- Changes `GET /api/projects` query and response contracts, the project
  application service signature, the studio store's project read port, the
  Drizzle project schema (index only), the OpenAPI baseline, generated
  frontend types, API parsing, the library bootstrap hook, and the project
  library page.
- The list contract is intentionally breaking for clients that read
  `settings` or `import_hash` from it. Such clients must use the project
  shell/detail surface; no new public detail route is added by this change.
- The schema change is one additive generated migration
  (`CREATE INDEX idx_projects_owner_updated_id`); no column, row, or data
  transition is required.
- No dependency, environment variable, route path, project create/update/
  detail/delete contract, or error-envelope change is required.

## Non-goals

- No offset pagination, total count, automatic cursor traversal, or infinite
  scroll.
- No pagination or payload redesign for project shells, editorial reviews,
  export catalogs, or any other list surface; each remains a named separate
  change (see `2026-09-03-paginate-revision-history`).
- No change to project creation seeding, settings updates, deletion, import
  idempotency, or the stable total order itself.
- No cross-owner browser cache: the library holds one page-scoped list per
  session mount, so the eight-owner LRU budget of the revision history cache
  has no analogous surface here; only the loaded rows are retained.

## Validation

- Store/API traversal tests for default/minimum/maximum limits, stable
  newest-first order, tie-break by id, nullable terminal cursor, complete
  traversal without duplicates or gaps, newer updates not entering an older
  traversal, owner scoping, and settings/import_hash exclusion.
- Cursor contract tests for malformed, oversized, non-canonical, truncated,
  unknown-version, out-of-range, and cross-owner tokens proving 422
  `VALIDATION_ERROR`, authentication precedence, and no store access.
- Query-plan evidence that the page query uses the covering index without a
  temporary sort and selects no `settings_json`.
- Frontend contract tests for strict page parsing, bounded first-page load,
  explicit older-page append with de-duplication, failure preservation, and
  accessible loading states.
- OpenAPI and generated-type deliberate refresh with drift checks, server and
  frontend full local suites, and strict OpenSpec validation.
