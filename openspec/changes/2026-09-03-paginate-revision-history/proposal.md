# Paginate document revision history

## Why

The revision-history endpoint currently returns every immutable revision in one
response, including each complete Markdown body and metadata object. It also
recomputes every word count from those bodies on every read. Because autosave
reloads that complete history after each successful save, a document with `N`
revisions and body size `B` accumulates roughly `O(BN²)` history-read work.

The frontend retains those unbounded responses in module-global maps keyed by
every project/document visited during the browser session. Long-lived writing
sessions therefore keep both network and browser memory proportional to total
history rather than to the history the author deliberately opened.

## What Changes

- Return revision history as newest-first summary pages through an opaque,
  project-and-document-bound keyset cursor ordered by
  `(revision_number DESC, id DESC)`, with a default page of 50 and maximum of
  100.
- Return `{ revisions, next_cursor }`. Revision summaries retain identity,
  parent, number, source, exact word count, and creation time, but exclude
  `content_markdown` and `metadata`.
- Persist the exact existing Unicode-aware word count on every immutable
  revision and backfill earlier rows in bounded, restart-safe batches before
  the server accepts traffic.
- Keep restore exact: the restore command resolves the selected revision's
  complete body and metadata internally by scoped revision id; the browser
  never needs a full revision-list payload.
- Replace post-autosave whole-history reloads with a bounded first-page refresh,
  add an accessible explicit "Load older revisions" action, and preserve
  project/document ownership, abort, stale-response, and restore-focus rules.
- Bound the shared browser cache to eight project/document owners and evict the
  least-recently-used inactive owner together with its request-version state.

## Impact

- Changes `GET /api/projects/:projectId/documents/:documentId/revisions` query
  and response contracts, revision application/persistence ports, the revision
  row schema, OpenAPI baseline, generated frontend types, API parsing, Studio
  revision state, and the History panel.
- The list contract is intentionally breaking for clients that read revision
  bodies or metadata from it. Such clients must use workflow-specific commands;
  no new public full-revision detail route is added by this change.
- The schema change and nullable-to-populated data transition ship through a
  generated migration plus a context-owned pre-serve reconciliation. Existing
  revision text, metadata, identity, parentage, number, source, and timestamps
  remain unchanged.
- No dependency, environment variable, route path, save success payload, or
  restore request/response change is required.

## Non-goals

- No offset pagination, total count, automatic traversal, retention/deletion,
  revision-body preview, diff viewer, or new public revision-detail endpoint.
- No pagination or payload redesign for project shells, editorial reviews,
  project catalogs, or export catalogs; each remains a named later change.
- No attempt to bound explicitly loaded visible history to one page. Additional
  pages enter the UI only after an author action; the cross-owner cache, not the
  currently visible author-selected list, owns the eight-owner limit.
- No change to optimistic save conflicts, immutable revision chains, restore
  semantics, document autosave timing, or revision-source vocabulary.

## Validation

- Store/API traversal tests for default/minimum/maximum limits, stable order,
  nullable terminal cursor, concurrent newer saves, boundary deletion,
  ownership, malformed/cross-project/cross-document cursors, and body/metadata
  exclusion.
- Migration and reconciliation tests proving exact Unicode word-count backfill,
  bounded batches, restart after partial progress, new-write population, backup
  ordering, and fail-before-serve behavior.
- Frontend contract/cache tests for first-page merge after autosave, explicit
  older-page append, de-duplication, coalescing, error preservation, LRU
  eviction, stale/aborted responses, project/document switches, and accessible
  loading/focus states.
- OpenAPI and generated-type drift, migration-channel, server/frontend full
  tests, Playwright History workflow, strict OpenSpec, and fixed-SHA evidence.
