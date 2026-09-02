# Bounded project shell and explicit current-document resource

---
status: accepted
---

Project open is split into a bounded structural shell and one explicit current
Document. `GET /api/projects/:projectId` and project creation return project
fields, ordered volumes, and document summaries; they do not return Markdown,
revision metadata, or revision source for every document. A new owner-scoped
`GET /api/projects/:projectId/documents/:documentId` returns the existing full
Document projection for exactly one current revision.

This decision **locally supersedes** ADR-0003's cutover-time adjudication that
removed the single-document GET route under #246 `ACCEPT-LOSS`. That removal was
correct for executing the Python-to-TypeScript contract switch; it is not a
permanent prohibition on a newly specified resource. ADR-0003 remains fully in
force for the TS-only tree, empty-database one-way door, `python-final` archive,
version authority, OpenAPI ownership, and Node-only operations.

## Context

The current project-detail projection joins every Document to its current
Revision and serializes every body and metadata object before the editor knows
which Document is active. Reorder returns the same full rows. The browser also
starts unrelated Review and Export reads during project bootstrap. A normal
open therefore scales with total manuscript bytes and unrelated histories,
couples navigation errors to editor errors, and gives late aggregate responses
an opportunity to replace a newer save.

The product already has the identity needed for a deeper boundary: each
Document points to one immutable current Revision, and every save is
conflict-checked against that identity. An explicit current-document resource
can use the shell's pointer as a causal cache key without treating it as
authorization or historical body authority.

## Decision

### Shell is structural authority

The shell owns project scalars, volume structure, document identity/placement,
current revision id, and exact current word count. Document summaries omit
`content_markdown`, `metadata`, and `revision_source`. Whole-project reorder
returns those summaries. The server uses a dedicated summary projection; it
does not hydrate full Documents and then drop fields during serialization.

### Current Document is an explicit scoped resource

The current-document GET returns one complete current Document at the existing
resource path. Authentication precedes lookup. After authentication, project,
document, and Owner scope are checked together and all missing/foreign cases
share one 404 boundary. The route does not expose arbitrary immutable Revision
bodies; restore and Snapshot workflows keep their existing internal authority.

### One active accepted body, separate from the Draft

The frontend retains at most one active complete Document per mounted Studio
project surface and reuses it only when project, document, and current revision
identities match the shell. Owner/revision epochs and abort prevent late reads
or older mutation results from publishing. Inactive bodies are not cached.

The editor's Draft is separate component-local state. The 1.5-second debounce
starts a save attempt; it is not a durability guarantee. A conflict retains the
Draft while its Document remains active, but deliberate switching or reload
still discards it. Accepted cache state never becomes silent Draft recovery.

### Inspector histories activate on demand

Review and Export histories load only when their URL-backed Inspector panel is
selected. Shell, current Document, Review, and Export have independent pending,
failure, retry, abort, and stale-response ownership. This removes unrelated
bootstrap work but does not claim to solve the still-unbounded Review/Export
list contracts; pagination and Review issue N+1 work require separate changes.

## Consequences

- Project open selects only structural/scalar columns plus one chosen body,
  with fixed query-count evidence independent of document count.
- Project detail, project creation, and reorder are breaking response changes;
  the server, OpenAPI baseline, generated types, and bundled frontend must land
  atomically.
- Navigation remains usable when one body or one Inspector history fails, and
  error recovery no longer clears unrelated surfaces.
- External clients needing a body follow a document summary to the scoped
  current-document resource; no `include=body` compatibility mode exists.
- No database migration, second backend, Python compatibility surface,
  background prefetch, offline Draft store, or inactive body cache is added.
- Review pagination/N+1, Export pagination, and project-catalog pagination stay
  explicitly deferred and must not be described as solved by lazy loading.

## Alternatives rejected

- **Keep aggregate project detail and optimize JSON parsing:** database,
  serialization, network, and browser-memory cost remain proportional to total
  manuscript bytes.
- **Add an opt-in summary query:** it preserves an unsafe full-body default and
  forces two project-detail contracts through every cache and caller.
- **Batch-fetch every body after the shell:** it recreates aggregate
  materialization and weakens failure isolation.
- **Cache inactive Documents or Drafts in a global LRU:** it adds memory and
  conflict semantics without a product requirement; one active accepted body
  is sufficient.
- **Load all Inspector histories once the shell succeeds:** it preserves
  unrelated startup amplification and coupled failure ownership.
