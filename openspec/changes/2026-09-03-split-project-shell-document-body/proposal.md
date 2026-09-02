# Split project shell from current document body

## Why

Opening a Studio project currently materializes every document's complete
current Markdown body and metadata even though navigation, ordering, and most
project chrome need only document identity and placement. The frontend then
starts review and export history reads during the same bootstrap regardless of
which Inspector panel the author selected. Project-open cost therefore grows
with the aggregate manuscript body plus unrelated histories instead of with the
one document being edited.

The combined payload also makes the project response and the editor's active
document share one lifecycle. A late project read can replace a newer saved
document, while a document failure can unnecessarily take down navigation.
The existing draft language compounds that ambiguity by calling the
1.5-second debounce a bound on loss even though a started save can fail or
conflict, and by not distinguishing an accepted-document cache from an
unsaved Draft.

## What Changes

- Replace project detail and project creation responses with a strict project
  shell containing project fields, volume rows, and lightweight document
  summaries. Summaries keep the current revision identity and word count needed
  for navigation and causal reads but exclude Markdown, revision metadata, and
  revision source.
- Add an explicit owner-scoped
  `GET /api/projects/:projectId/documents/:documentId` resource for one complete
  current Document, with authentication before scoped lookup and the same 404
  boundary for missing, foreign-project, and non-owned resources.
- Return document summaries, not complete Documents, from whole-project reorder
  so moving one row cannot retransmit every document body.
- Split frontend project state into a project-shell owner and a one-active-
  document owner. A cached accepted Document is usable only when its project,
  document, and current revision exactly match the shell pointer; request
  ownership, shared-subscriber lifetime, bounded mismatch recovery, abort, and
  mutation intent/revision identity prevent stale publication.
- Bootstrap authoring with the shell and at most the selected current Document.
  Load review and export histories only when their route-backed Inspector panel
  is selected, with independent pending, failure, and retry state.
- Clarify that the debounce starts a save attempt rather than guaranteeing
  durability, that accepted-document cache state is not a Draft, and that a
  conflict retains the active local Draft until the author resolves it or
  explicitly leaves that document.
- Record the deliberate current-document resource as a local supersession of
  ADR-0003's cutover-time single-document GET `ACCEPT-LOSS`; the rest of the
  executed cutover remains unchanged.

## Impact

- Changes the response contract of `GET /api/projects/:projectId`,
  `POST /api/projects`, and
  `PUT /api/projects/:projectId/documents/reorder`; adds one read route at the
  existing document resource path.
- Affects project/document payload schemas and builders, Studio store and
  application read ports, OpenAPI baseline, generated frontend types, API
  parsers, project bootstrap, active-document state, Inspector data ownership,
  tests, and ADR documentation.
- The contract is intentionally breaking for clients that read a document body,
  metadata, or revision source from project detail or reorder responses. Such
  clients must follow a summary to the scoped current-document resource.
- No database migration, new index, dependency, environment variable, write
  semantic, autosave interval, revision rule, Review payload, or Export payload
  is required.

## Non-goals

- No pagination, summary/detail split, issue batching, or N+1 repair for Review
  history; those remain a separate change.
- No pagination or retention change for Export history or the project catalog;
  those remain separate changes.
- No document-body page cache, offline Draft recovery, local-storage Drafts,
  background prefetch, automatic traversal, or speculative body loading.
- No change to save/restore/proposal response bodies, conflict resolution,
  immutable revisions, snapshot authority, volume semantics, or full-text
  search.

## Validation

- Contract-first store/API coverage for exact shell and summary shapes,
  body/metadata exclusion, current-document fidelity and scope, reorder
  projection, authentication-before-disclosure, and separately bucketed fixed
  authentication and Studio-projection query budgets.
- Frontend state tests for initial request bounds, summary-to-body selection,
  bounded shell/body convergence after a revision mismatch, concurrent full and
  partial mutation/read ordering, project/document switches, reference-counted
  abort/unmount, mandatory coalesced-consumer fanout, resource-specific
  navigation/error recovery, and precise Draft/conflict behavior.
- Playwright project-open, switching, reorder, Review, Export, failure/retry,
  keyboard, and Back/Forward workflows against the TypeScript backend.
- OpenAPI/generated-type drift, server/frontend full gates, strict OpenSpec,
  and independent fixed-SHA standards, architecture, concurrency, and UX
  reviews with every skip recorded.
