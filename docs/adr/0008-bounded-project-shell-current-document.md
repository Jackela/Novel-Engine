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

Public query evidence separates the production guard from the Studio
projection: a valid session has a fixed two-statement authentication cost
(session lookup plus last-seen update), while shell and current-Document
projections have their own at-most-three and at-most-two statement budgets.
Every traced statement must belong to one of those buckets; body/metadata
exclusion is asserted on the real shell projection rather than inferred from
the serialized response.

### One active accepted body, separate from the Draft

The frontend retains at most one active complete Document per mounted Studio
project surface and reuses it only when project, document, and current revision
identities match the shell. Equal project/document/expected-revision/lifecycle
reads coalesce behind one reference-counted request, notify every surviving
subscriber, and abort only after the last subscriber releases ownership.
Owner/revision epochs and abort prevent late reads or older mutation results
from publishing. Inactive bodies are not cached.

Because a revision can advance between shell and body reads, an unexpected body
revision is never rendered directly. The client refreshes shell once, accepts
the response only if that pointer now matches, or performs one replacement body
read for the refreshed pointer. A second mismatch stops automatic work and
shows explicit Retry while retaining the latest shell. Each automatic mismatch
cycle is therefore bounded to one shell refresh and one replacement body read.

Complete-Document write responses update shell and accepted body only under
current causal revision ownership. Lore-status and beat-association responses
retain their narrow payloads and are gated by project, Document, field-specific
intent epoch, and requested value. This prevents an older same-revision response
from reversing a newer intent without pretending the narrow response is a full
Document.

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

Failure navigation remains global where identity is global: any project-
resource 401 replaces to Entry, and shell 404 replaces to the project library.
A current-Document 404 refreshes shell before selecting a fallback or showing a
scoped inconsistency; Review/Export 404 likewise rechecks project existence.
Only network, timeout, contract, and server failures remain on local resource
recovery surfaces.

## Consequences

- Project open selects only structural/scalar columns plus one chosen body,
  with fixed query-count evidence independent of document count.
- Project detail, project creation, and reorder are breaking response changes;
  the server, OpenAPI baseline, generated types, and bundled frontend must land
  atomically.
- Navigation remains usable when one body or one Inspector history fails, and
  error recovery no longer clears unrelated surfaces.
- A changing Document cannot trigger an unbounded shell/body retry loop, and an
  initiating subscriber cannot suppress another consumer's result by unmounting.
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
