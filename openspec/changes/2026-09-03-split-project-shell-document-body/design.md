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
request returns 401 without consulting project, document, or revision state.
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
requires current revision body or metadata. The production path reads no
`content_markdown` or revision `metadata_json` column and performs at most three
SQL statements independent of project document count: scoped project, ordered
document summaries joined to their current revision scalar projection, and
ordered volumes. It may use fewer statements, but tests pin the upper bound and
column exclusion at the real store seam.

The current-document path performs at most two SQL statements independent of
project size: scoped project/authorization if it is not folded into the next
statement, then one project-and-document-scoped current-revision read. It
selects one body's complete fields and never hydrates sibling documents.
Execution tracing must prove both budgets through public application/API calls;
copied SQL or mocks are not evidence. Query-plan evidence must show indexed
project/document/current-revision access and no scan proportional to all
revision history.

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

A missing body or any pointer mismatch starts the scoped GET. Equal owner and
expected-revision requests may coalesce and must notify every still-mounted
subscriber. Requests for another owner or expected revision cannot coalesce.
Each request captures project/document ownership, expected revision, and a
monotonic lifecycle epoch; success publishes only if all still match. A late
response from a previous project, document, or revision is discarded.

No inactive complete-document entries are retained by this state machine.
Switching selection aborts the previous cancellable read, clears its accepted
body from active state, and publishes a loading state for the next selection.
The last subscriber's unmount aborts its request and removes request
bookkeeping. This one-active-owner boundary is the memory budget; adding an LRU
of inactive document bodies is explicitly outside this change.

Successful create, save, restore, lore-status, beat, placement, or accepted
proposal commands already return a complete Document. Their returned project,
document, and current revision identities may atomically update both the shell
summary and active accepted Document. A response for an older base/current
revision cannot overwrite a newer mutation result. Reorder updates only shell
positions and preserves the active accepted body when its identity remains
unchanged.

The authoring bootstrap first resolves the shell, chooses the route-compatible
active document, and reads at most that one complete Document. It never follows
other summaries to prefetch sibling bodies. A shell failure owns the project
surface error. A current-document failure leaves shell navigation available,
shows a readable editor-local error and Retry action, and does not masquerade as
an empty document. Retry retains the same expected revision unless a fresher
shell changed it.

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
failure, abort, retry, and stale-response ownership. Review failure must not
clear the editor, block Export, or appear as a project-shell error; Export
failure follows the symmetric rule. Leaving a panel aborts a cancellable
in-flight read or prevents its late response from becoming the visible state.
Returning to a failed panel exposes its retry without manufacturing an empty
history. Loading one selected panel never triggers the other.

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
