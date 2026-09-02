# Design: bounded project shell with one causally owned current Document

## Authority split

Project detail currently mixes three authorities that change at different
rates: project/navigation structure, one current accepted Document, and the
editor's unsaved Draft. The new boundary gives each one an explicit owner:

- the **project shell** owns project fields, volume structure, document
  identity/placement, and each document's current revision pointer;
- the **current Document resource** owns one accepted body, metadata object,
  revision source, and word count at that pointer;
- the **Draft** remains component-local editor state and is never written into
  either cache until a save succeeds.

The project shell returned by `GET /api/projects/:projectId` and
`POST /api/projects` is a strict object with the existing project scalar fields,
required `documents`, and required `volumes`. Each document summary contains
exactly:

- `id`
- `project_id`
- `kind`
- `title`
- `position`
- `volume_id`
- `beat_ref`
- `lore_status`
- `current_revision_id`
- `word_count`
- `created_at`
- `updated_at`

It omits `content_markdown`, `metadata`, and `revision_source`; those fields are
absent, not nullable. `current_revision_id` is retained as the causal identity
of the accepted body, and `word_count` remains a cheap navigation/editor size
signal backed by the persisted revision count. Volume fields and project scalar
fields keep their existing meanings and closed schemas.

`PUT /api/projects/:projectId/documents/reorder` returns the same document
summary projection after committing the whole-set order. Create and save
commands continue returning one complete Document because their result is the
new accepted state the editor should publish without a follow-up read.

## Explicit current-document resource and authorization order

`GET /api/projects/:projectId/documents/:documentId` returns the existing strict
complete Document shape for that document's current immutable revision. It is a
current projection, not an arbitrary revision-detail endpoint. Historical body
authority remains private to the restore workflow and snapshots.

The principal guard runs before project/document lookup. An unauthenticated
request returns 401 without consulting project, document, or revision state;
the frontend treats that 401 as a global session loss and replaces to Entry.
After authentication, the application performs one owner-and-project-scoped
lookup: a missing document, a document belonging to another project, and a
document outside the principal's scope produce the same existing 404 code,
message, and envelope. The route never accepts a project or revision identity
from query data and never treats the shell pointer as authorization.

This route deliberately supersedes only ADR-0003's cutover-time decision to
drop the former single-document GET. It does not revive a second backend,
restore any Python compatibility contract, or change the cutover's one-way data
door.

## Read projection and query budgets

The store exposes distinct `ProjectShell`, `DocumentSummary`, and complete
`DocumentWithCurrent` read ports. A shell query must never reuse a mapper that
requires current revision body or metadata. Query accounting is split into
named trace buckets so authentication is neither omitted nor accidentally
charged to the Studio projection:

- a successful authenticated public request has a fixed **auth** cost of two
  statements in the production path: session lookup and last-seen update;
- after the Principal exists, the **shell projection** performs at most three
  statements independent of project document count: scoped project, ordered
  document summaries joined to current revision scalar fields, and volumes;
- after the Principal exists, the **current-Document projection** performs at
  most two statements independent of project size: scoped project/document
  resolution and the one complete current-revision projection.

The shell projection reads no `content_markdown` or revision `metadata_json`
column. The current-Document projection selects one body's complete fields and
never hydrates sibling documents. Public-route tracing must attribute every
statement to `auth` or the named Studio projection, assert the fixed auth cost
separately, and prove the combined request equals the sum of those buckets.
Execution tracing must use real store/application/API calls; copied SQL or mocks
are not evidence. Query-plan evidence must show indexed project/document/
current-revision access and no scan proportional to all revision history.

Reorder still validates the full document-id set and updates the whole order,
so its write work remains proportional to the number of documents. Its response
read/serialization is nevertheless summary-only and must not hydrate any body
or metadata. This change makes no false constant-query claim for the write
transaction.

## Frontend shell and active-document state

The project hook owns the shell; a separate active-document state machine owns
at most one project/document pair for a mounted Studio project surface. It may
reuse an already accepted complete Document only when all three identities
match the selected shell row:

`(project_id, document_id, current_revision_id)`.

A missing body or any pointer mismatch starts the scoped GET. Requests with the
exact same `(projectId, documentId, expectedRevisionId, lifecycleEpoch)` MUST
coalesce. The shared request holds a reference count, publishes success or
failure to every still-mounted subscriber, and is aborted only when its last
subscriber leaves. Releasing one subscriber suppresses delivery only to that
released subscriber or its obsolete owner; every surviving subscriber still
receives the shared outcome. Requests differing in any tuple member cannot
coalesce. Each request captures that tuple; success publishes only to consumers
for which it still matches. A late response from a previous project, document,
revision, or lifecycle is discarded only for that obsolete ownership.

The GET cannot promise that the revision stays unchanged between shell and body
reads. If its response `current_revision_id` differs from the expected shell
pointer, the client never renders that response blindly. It performs one fresh
shell read. If the refreshed shell says the project no longer exists, the route
replaces to the project library. If it says the Document no longer exists, the
Studio selects the route-compatible fallback or no-Document state and performs
no replacement read for the vanished identity. When the refreshed summary for
that same Document equals the response revision, the response may publish under
the refreshed owner. Only when that summary still exists with a different
pointer does the client issue one replacement current-Document read owned by
the refreshed pointer. If that replacement also mismatches because the
Document keeps changing, automatic convergence stops: the latest shell remains
visible and the editor shows a readable changed-again error with an explicit
Retry. One mismatch cycle is thus bounded to one shell refresh and at most one
replacement body read; Retry starts a new cycle rather than an unbounded loop.

No inactive complete-document entries are retained by this state machine.
Switching selection releases that subscriber, clears the accepted body from its
active state, and publishes a loading state for the next selection. A shared
read continues for surviving subscribers; only the last subscriber's unmount or
owner release aborts it and removes request bookkeeping. This one-active-owner
boundary per mounted surface is the memory budget; adding an LRU of inactive
document bodies is explicitly outside this change.

Successful Document creation, save, restore, placement, and accepted-proposal
commands that return a complete Document may atomically update both the shell summary
and active accepted Document when their causal revision/owner identity is
current. Lore-status and beat-association commands keep their existing narrow
local payloads; they do not fabricate a complete Document. Each narrow command
captures project, Document, field-specific intent epoch, and requested value.
On success it first validates that the active shell still contains that exact
captured project/Document identity and that its field-specific epoch remains
latest. It then MUST patch only its owned summary field: `lore_status` from the
closed response value, or `beat_ref` from the returned resolved beat title/null.
A failed identity/epoch check is stale and MUST be ignored. Reverse-order same-
revision responses therefore cannot replace a newer Lore-status or beat intent.
A response for an older revision or mutation intent cannot overwrite a newer
result. Reorder updates only shell positions and preserves the active accepted
body when its identity remains unchanged.

The authoring bootstrap first resolves the shell, chooses the route-compatible
active document, and reads at most that one complete Document. It never follows
other summaries to prefetch sibling bodies. Failure classification is
resource-specific. Any authenticated resource's 401 is global session loss and
replaces to Entry. A shell 404 replaces to the project library. A current-
Document 404 first refreshes the shell: if the project is gone it replaces to
the library; if the document disappeared it selects the route-compatible
fallback summary (or the documented no-document editor state); if the refreshed
shell still names the document, the editor shows a scoped inconsistency with
Retry. Only network, timeout, contract, and server failures stay on their local
shell/editor recovery surface. Retry retains the same expected revision unless
a fresher shell changed it.

## Draft and conflict semantics

The accepted Document cache and the Draft are distinct values. Typing copies
the accepted title/content into editor-local Draft state. After 1.5 seconds of
idle time, autosave starts a conflict-checked request; the debounce is not a
durability promise. Until success returns, failure, cancellation, and process
loss can leave that Draft unaccepted.

A 409 retains the local Draft and a separately loaded server baseline while the
document stays active, as the existing conflict contract requires. Choosing a
conflict action resolves which value advances. Deliberately switching documents
or reloading still discards the unresolved local Draft; it must not be smuggled
into the accepted-document state or retained as a per-document inactive Draft.
Late save or conflict reads cannot publish editor state into the newly selected
document. If a save committed before its client response was abandoned, the
next shell/current-document read converges from SQLite authority.

## Lazy Inspector histories and independent failures

Project bootstrap no longer requests Review or Export history. The URL-backed
Inspector selection remains the owner: selecting Review activates its existing
read, selecting Export activates its existing read, and direct navigation or
Back/Forward performs the same activation. A panel may retain its last
successful response for the mounted project, but it does not prefetch while
never selected.

Shell, current Document, Review, and Export each have independent pending,
failure, abort, retry, and stale-response ownership. A 401 from any is global
session loss. A shell 404 returns to the project library; a Review or Export 404
refreshes shell ownership before choosing library navigation or, when the shell
still exists, classifying the impossible scoped miss as a panel-local contract
failure. Operational Review failure must not clear the editor, block
Export, or appear as a project-shell error; Export failure follows the symmetric
rule. Leaving a panel releases its read subscriber or prevents its late response
from becoming visible. Returning to a failed panel exposes its retry without
manufacturing an empty history. Loading one selected panel never triggers the
other.

The existing Review and Export list response shapes remain unchanged in this
change. Their unbounded rows, Review issue hydration/N+1 behavior, and later
pagination/detail designs are explicitly deferred; lazy activation reduces
unrelated startup work but is not presented as a complete bound on those
histories.

## Compatibility and rollout

The server and bundled frontend migrate atomically with the deliberate OpenAPI
baseline and generated types. External clients that used project detail or
reorder as a body collection must perform the explicit scoped document read.
There is no compatibility flag or `include=body` escape hatch because either
would preserve the unbounded default and duplicate response contracts.

No schema migration is required. The change stays active until full local
validation, TypeScript-backend Playwright workflows, independent fixed-SHA
reviews, and required CI are green. Only then may its delta merge into the
canonical capability spec and the change archive.

## Options rejected

- Keeping full Documents but lazily parsing bodies still pays database,
  serialization, network, and browser-memory cost.
- Adding `?include=documents` or `?summary=true` keeps an unsafe default or two
  project-detail shapes and makes cache ownership conditional.
- Returning a map of every body from a second batch endpoint recreates the same
  aggregate materialization behind another route.
- Retaining inactive body or Draft entries in a module-global LRU adds memory
  and conflict semantics with no requirement; one active accepted Document is
  sufficient.
- Loading Review and Export together after the shell is simpler wiring but
  preserves unrelated bootstrap amplification and coupled error state.
- Treating the 1.5-second debounce as guaranteed durability hides network,
  conflict, and cancellation failure windows and contradicts recoverable
  conflict behavior.
