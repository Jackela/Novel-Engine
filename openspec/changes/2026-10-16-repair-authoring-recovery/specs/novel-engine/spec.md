## MODIFIED Requirements

### Requirement: Save request semantics
A document save MUST accept new content together with an optional new title
and metadata in the same request. Every accepted save MUST create a revision
numbered exactly one greater than the document's current revision number,
with the current revision as its parent, keeping numbering monotonic per
document. The revision source MUST be a server-assigned closed enum of
`author`, `ai-accepted`, and `restore`; the save request schema MUST NOT
expose a source field.

A save MAY be marked as the editor's autosave (the `autosave` request field,
default false). Marked saves additionally apply the revision growth policy:

- a save whose body, metadata, and title already match the current revision
  MUST write nothing — no revision row, no index rewrite, no timestamp;
- an autosave whose unreferenced `author` predecessor was written inside the
  collapse window (30 seconds) MUST fold that predecessor into the new
  revision: the predecessor row is deleted and the new revision inherits the
  predecessor's parent, so the lineage chain keeps no dangling reference;
- an autosave MUST prune unreferenced `author` revisions older than the
  retention window (90 days) that fall outside the newest 200 revisions of
  the document, deleting at most one bounded batch per save and repairing the
  `parent_revision_id` pointer of surviving children past pruned ancestors.

The newest-200 protection MUST count existing retained Revision rows rather
than gaps in monotonic revision numbers left by autosave folding.

A save that would reuse another Document's title within the same project and
document kind MUST return 409 `DOCUMENT_CONFLICT`. It MUST leave the current
Revision, title, content, revision history, search index, and project update
time unchanged. A stale base Revision MUST continue to return
`REVISION_CONFLICT` before a title collision is considered.

Revisions referenced by a snapshot, the document's current revision, and the
document's first revision MUST never be folded or pruned; revision content and
metadata stay immutable, and only the lineage pointer of a surviving revision
may be repaired. Non-autosave saves (restores, accepted proposals, imports)
keep plain append semantics.

#### Scenario: Title and metadata change in the same save
- **GIVEN** a document points to revision A and is titled "Chapter 1"
- **WHEN** the author saves new content, a new title, and new metadata based
  on revision A
- **THEN** the created revision carries the new content
- **AND** the document's title and metadata reflect the same request
- **AND** the document advances to the new revision in one operation

#### Scenario: Revision numbering is monotonic with an unbroken chain
- **GIVEN** a document's latest revision is number 5
- **WHEN** two sequential saves based on the then-current revision succeed
- **THEN** the created revisions are numbered 6 and 7 in order
- **AND** each created revision's parent is the revision it was saved against

#### Scenario: Source is assigned by the server
- **GIVEN** a client attempts to supply a source value with a save
- **WHEN** the request is validated and executed
- **THEN** no client-supplied source is accepted
- **AND** the created revision's source is one of `author`, `ai-accepted`,
  or `restore`, as determined by the operation the server performed

#### Scenario: Repeated autosave of the current content writes nothing
- **GIVEN** a document points to revision A whose body and metadata match the
  incoming save
- **WHEN** the save is marked as an autosave
- **THEN** no revision is created
- **AND** the document keeps pointing to revision A with an unchanged update
  timestamp, and the search index is not rewritten

#### Scenario: Adjacent autosaves fold into the newest state
- **GIVEN** a document points to revision A, which is an unreferenced `author`
  revision written 2 seconds ago
- **WHEN** an autosave based on revision A succeeds
- **THEN** revision A is deleted and the new revision's parent is A's parent
- **AND** the new revision is the document's current revision

#### Scenario: Snapshot-pinned revisions are never folded or pruned
- **GIVEN** an old revision is referenced by a snapshot document
- **WHEN** an autosave inside the collapse window, and later a retention
  prune, consider unreferenced predecessors of that document
- **THEN** the pinned revision remains readable and unchanged

#### Scenario: The first Revision survives retention

- **GIVEN** the first Revision is older than 90 days and lies outside the newest 200 retained Revisions
- **WHEN** an autosave prunes eligible old author Revisions
- **THEN** the first Revision remains readable
- **AND** surviving parent pointers continue to name retained ancestors

#### Scenario: Folded numbering gaps do not shrink the retained-history floor

- **GIVEN** autosave folding has advanced the current Revision number beyond 200 while fewer than 200 Revision rows remain
- **WHEN** an autosave evaluates old author Revisions for retention
- **THEN** none of those retained rows is deleted merely because its number is more than 200 below the current number

#### Scenario: A conflicting title rejects the whole save

- **GIVEN** two Documents of the same kind in one project have distinct titles
- **WHEN** one is saved with the other Document's title and a current base Revision
- **THEN** the response is 409 `DOCUMENT_CONFLICT`
- **AND** the title, content, current Revision, complete retained history, search index, and project update time remain unchanged


### Requirement: In-memory document drafts

An unsaved Draft—edited content, title, and save state—MUST live only in the
currently active editor's component memory. Leaving a Document MUST NOT retain
that Draft as client-side state for an inactive Document: it MUST NOT be
restored from inactive client memory or client-side storage across selection
changes, route departure, or page reload. A cached complete Document represents
only a server-accepted revision and MUST NOT store or be mutated into an
unsaved Draft.

A Draft that has not been accepted MUST NOT be dropped silently when its owner
is left. While an edited Draft has not been accepted, a deliberate selection of
another Document, or leaving the Studio surface with that Document open, MUST
hand the departing Document's newest local content and title to one rescue
write — one conflict-checked draft save addressed to that Document. The
departure MUST NOT duplicate a save attempt already in flight for that Document
with identical content and title, an unresolved conflict Draft MUST NOT enter
the rescue path, and the departing editor's local Draft is discarded once the
rescue write is issued. The rescue's result is observable only as an accepted
revision of its own Document: reopening that Document MUST read the rescued
text back from the server rather than from inactive client state, and MUST NOT
save it again. A rescue write that fails, conflicts, or never lands MUST remain
silent and MUST NOT claim acceptance; the next open reads the server state, and
the explicit save surface keeps ownership of user-visible save errors.

After 1.5 seconds without a newer edit, the Studio MUST start the existing
conflict-checked autosave attempt. The debounce bounds when an attempt starts;
it MUST NOT be presented as a guarantee that the Draft is durable, because a
request can fail, conflict, be cancelled, or lose its response. A 409 `REVISION_CONFLICT` MUST
retain the local Draft and a separate latest-server baseline while that
Document remains active. The active local Draft ends only by successful
acceptance, an explicit conflict choice that replaces it, a departure that
hands the newest text to its one rescue write, or a reload. A late save,
rescue, or conflict outcome MUST NOT publish into a newly active Document.

Automatic retries MUST NOT repeat an unchanged Draft after a permanent HTTP
413 or 422 save refusal. The active Draft and its visible error MUST remain
available for correction or an explicit retry. Editing that Draft MUST resume
the ordinary debounced save path. Transient transport failure retry and the
explicit `REVISION_CONFLICT` path MUST retain their existing behavior. A
409 `DOCUMENT_CONFLICT` MUST retain the Draft as an editable save error,
without presenting revision-conflict replacement actions or automatically
repeating the unchanged title.

#### Scenario: Switching documents discards the draft

- **GIVEN** the active Document has unsaved edits and no unresolved conflict Draft
- **WHEN** the author deliberately switches to another Document
- **THEN** exactly one save for the departing Document carries its newest local content and title as that Document's rescue write
- **AND** the departing editor's local Draft is discarded and no client-side Draft copy remains
- **AND** the next Document loads from its accepted current revision
- **AND** a late response for the earlier Document cannot replace the new editor state

#### Scenario: Leaving the Studio rescues the pending draft once

- **GIVEN** the author edits a Document and leaves the Studio before the 1.5-second debounce elapses
- **WHEN** the departure happens
- **THEN** exactly one rescue write for the departing Document carries its newest local content
- **AND** no write is issued for another Document or project
- **AND** waiting past the debounce window issues no duplicate late save

#### Scenario: A reopened document reads back the rescued text

- **GIVEN** a departure's rescue write was accepted as a revision of that Document
- **WHEN** the author opens that Document again
- **THEN** the editor shows the rescued content and title read back from the server, settled as saved
- **AND** re-entry issues no further save for that Document

#### Scenario: An unresolved conflict draft is not rescued

- **GIVEN** the active Document holds an unresolved conflict Draft
- **WHEN** the author deliberately switches to another Document
- **THEN** no rescue write is issued for the conflicted text
- **AND** the conflict Draft is discarded with the departure
- **AND** opening that Document again reads its last accepted revision

#### Scenario: A failed rescue write stays silent

- **GIVEN** a departure's rescue write fails or never lands
- **WHEN** the author opens that Document again
- **THEN** the editor shows that Document's last accepted revision
- **AND** no error, acceptance claim, or client-side Draft copy from the failed rescue is published

#### Scenario: No client-side draft persistence

- **GIVEN** unsaved edits
- **WHEN** the page reloads
- **THEN** the editor loads the last accepted current revision with no Draft recovery

#### Scenario: Debounce starts an attempt but does not claim durability

- **GIVEN** the author stops typing in an unsaved Draft
- **WHEN** 1.5 seconds elapse without a newer edit
- **THEN** the Studio starts a conflict-checked save attempt
- **BUT WHEN** that attempt fails, conflicts, or is cancelled
- **THEN** the product does not claim the Draft was accepted or durable

#### Scenario: Conflict retains the active local Draft

- **GIVEN** autosave receives a revision conflict while the same Document remains active
- **WHEN** the latest server Document is loaded as the conflict baseline
- **THEN** the local Draft remains separately available for the explicit conflict actions
- **AND** neither value silently overwrites the other

#### Scenario: A permanent size or validation refusal stops automatic retry

- **GIVEN** a save of the active Draft is refused with HTTP 413 or 422
- **WHEN** automatic retry intervals elapse without another edit
- **THEN** no further save request is sent for that unchanged Draft
- **AND** the local title, content, and readable save error remain available
- **WHEN** the author corrects the Draft
- **THEN** the ordinary debounced save may persist the corrected text


### Requirement: Guided lorebook initialization

The Studio MUST offer a project-scoped lorebook initialization wizard inside
a `lore` Inspector tab with URL-backed activation, turning draft material
the author already has into candidate Lore entries through a configured
provider. The wizard MUST accept text the author pastes and content of
already-existing project documents as extraction input, organized as
segments where each segment is one paste or one document's current content,
and MUST present extraction results as candidates — each carrying a
document kind limited to `character` or `world`, a title, suggested
aliases, and a summary body — that are suggestions, not persisted content.
Each segment MUST be extracted by its own `lore-extract` Job under the
synchronous job execution model, recording exactly one usage event per
completed provider request, and cross-segment candidate merging MUST happen
in the wizard session over the completed segment Jobs: same-kind,
same-title candidates collapse to one candidate carrying the union of
suggested aliases, in a deterministic order. Until the author explicitly
confirms, the wizard MUST NOT create any document, revision, or Lore
lifecycle state, and abandoning the wizard MUST leave the project's
lorebook unchanged.

On confirmation, each selected candidate MUST run two existing steps in
sequence — the existing lorebook document creation call, then the existing
Lore alias write path for that candidate's aliases — and the wizard MUST
report each candidate's outcome independently. The two steps MUST NOT be
presented as atomic: when the alias write fails after creation succeeds,
the wizard MUST report the candidate as created with failed aliases, keep
the suggested aliases available for retry, and MUST NOT silently drop
them. Confirmed entries MUST be created at `draft` lifecycle status. With
the trial (mock) provider the wizard MUST still produce deterministic
placeholder candidates per segment and MUST label the session with the
trial-mode wording used by the first-run explainer.

Every successfully created Document MUST immediately enter the current
project's navigation through the existing project-shell state owner, including
a Document whose alias write failed. This update MUST preserve the active Draft
and MUST NOT publish into another project. Within one wizard session, starting
over MUST allow work on uncreated candidates without reissuing creation for
already-created candidates. Outstanding failed alias writes MUST keep their
existing retry surface until resolved or the session is abandoned.

Each input segment MUST be capped at 100,000 Unicode code points. A segment
over the cap, or a segment whose assembled extraction prompt exceeds the
shared UTF-8 byte authority of proposal generation, MUST fail before
provider construction with the stable 422 `GENERATION_CAPACITY_EXCEEDED`
envelope and an `observed` value bounded to the refusing limit plus one —
never through silent truncation. The envelope details carry the fixed
combination of the refusing resource: a segment over the code-point cap
carries `resource: lore_extract_segment` with `limit: 100000`, and an
assembled prompt over the shared byte authority carries the shared
`prompt_bytes` combination of proposal generation. Any retrieval the wizard
performs over project content MUST behave like the product's full-text
search: operator-laden input safely reduced to strict tokens, irreducible
input returning no results, and every query running as a token-reduced
parameterized search.

#### Scenario: Draft material yields candidates

- **GIVEN** a project with a real provider configured
- **WHEN** the author pastes a draft excerpt and runs extraction for that segment
- **THEN** the segment's `lore-extract` Job completes and the wizard presents its candidate entries of kind `character` or `world`, each with a title, suggested aliases, and a summary body
- **AND** no document, revision, or Lore lifecycle state exists yet

#### Scenario: Trial provider yields labeled placeholder candidates

- **GIVEN** a project still on the built-in trial provider
- **WHEN** the author runs the wizard end to end
- **THEN** deterministic placeholder candidates are presented for each segment
- **AND** the session is labeled with the trial-mode wording so the author knows real extraction requires a configured provider

#### Scenario: Nothing persists before confirmation

- **GIVEN** the wizard has presented merged candidates from completed segment Jobs
- **WHEN** the author abandons the wizard without confirming
- **THEN** the project's lorebook, documents, and revisions are unchanged
- **AND** candidates cease to exist with the wizard session; only the segment Jobs' own audit records remain

#### Scenario: Confirmed candidates become draft Lore entries

- **GIVEN** the author selects a subset of the presented candidates and confirms
- **WHEN** confirmation completes
- **THEN** each selected candidate exists as a `character` or `world` document created through the existing creation path at `draft` lifecycle status, followed by the existing alias write for its suggested aliases
- **AND** unselected candidates create nothing
- **AND** each candidate's outcome is reported independently, so one candidate's failure does not hide another's result

#### Scenario: Alias write failure reports partial success

- **GIVEN** a confirmed candidate whose document creation succeeds but whose alias write fails
- **WHEN** the wizard reports that candidate's outcome
- **THEN** it reports the entry as created with failed aliases, not as failed and not as silently alias-less
- **AND** the suggested aliases remain available so the author can retry the alias write

#### Scenario: Confirmed entries reach prompts only through the existing gate

- **GIVEN** a confirmed wizard-created entry is still `draft`
- **WHEN** a proposal is generated whose corpus matches the entry's keys
- **THEN** the entry contributes nothing, exactly like any other `draft` entry
- **WHEN** the author promotes the entry to `stable` using the existing lifecycle editing
- **THEN** the entry participates in keyword-triggered injection like any other `stable` entry

#### Scenario: Over-budget segments fail closed

- **GIVEN** a segment exceeding 100,000 Unicode code points
- **WHEN** extraction is requested for that segment
- **THEN** the request fails before provider construction with 422 `GENERATION_CAPACITY_EXCEEDED` whose details carry `resource: lore_extract_segment`, `limit: 100000`, and an `observed` value of at most the limit plus one
- **AND** no provider work, no usage event, and no partial candidate set is produced for that segment
- **AND** the author is told to split or trim the segment rather than receiving silently truncated results

#### Scenario: Over-budget assembled prompts carry the shared refusal

- **GIVEN** a segment whose assembled extraction prompt exceeds the shared UTF-8 byte authority
- **WHEN** extraction is requested for that segment
- **THEN** the request fails before provider construction with 422 `GENERATION_CAPACITY_EXCEEDED` carrying the shared `prompt_bytes` combination of proposal generation, with `observed` bounded to that limit plus one
- **AND** no provider work, no usage event, and no partial candidate set is produced for that segment

#### Scenario: Multi-segment candidates merge deterministically

- **GIVEN** two completed segment Jobs whose candidate sets both include a character with the same title
- **WHEN** the wizard presents the merged list
- **THEN** one merged candidate of that kind and title appears, carrying the union of both segments' suggested aliases
- **AND** re-running the merge over the same completed segments yields the same list

#### Scenario: Extraction failures stay inside the provider diagnostics boundary

- **GIVEN** the provider transport receives an error response whose body the provider failure diagnostics boundary discards
- **WHEN** a segment's extraction fails and the wizard reports the failure
- **THEN** the failure surfaces through the Studio error surface with the standard error envelope
- **AND** the discarded upstream body text does not appear in the job error, the envelope, or any author-visible surface
- **AND** no Lore entry is created from the failed run

#### Scenario: Confirmation updates navigation without a reload

- **GIVEN** the wizard confirms a selected candidate in the current project
- **WHEN** document creation succeeds, whether or not its following alias write succeeds
- **THEN** the new draft Lore entry appears in the appropriate navigation group without a page reload
- **AND** the active editor Draft remains unchanged

#### Scenario: Starting over retries only uncreated candidates

- **GIVEN** one candidate was created and a second candidate's creation failed
- **WHEN** the author starts over and confirms the remaining candidate
- **THEN** creation is requested only for the candidate that was not created
- **AND** any outstanding alias failure on a created entry remains independently retryable

#### Scenario: Late confirmation cannot update a different project

- **GIVEN** confirmation began in one project
- **WHEN** the author switches to a different project before creation completes
- **THEN** the created Document is not inserted into the newly active project's navigation

