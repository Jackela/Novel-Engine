## MODIFIED Requirements

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
request can fail, conflict, be cancelled, or lose its response. A 409 MUST
retain the local Draft and a separate latest-server baseline while that
Document remains active. The active local Draft ends only by successful
acceptance, an explicit conflict choice that replaces it, a departure that
hands the newest text to its one rescue write, or a reload. A late save,
rescue, or conflict outcome MUST NOT publish into a newly active Document.

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

### Requirement: Project-scoped Studio resource lifecycle

The complete Studio workbench state MUST be owned by the current route
`projectId`. When that identity changes, data and pending state from the prior
project MUST become non-interactive immediately. Shell, active Document, Jobs,
Usage, search, Drafts, revisions, proposals, whole-book progress, Reviews,
Exports, settings, and errors MUST reset or remain keyed to their originating
project and resource owner. A late response from an earlier project, Document,
revision expectation, lifecycle, or field-specific mutation intent MUST NOT
overwrite the active Document, surface, error, revision baseline, Lore status,
or beat association.

Transports that support cancellation MUST be aborted when their last owner
releases them. Exact project/Document/expected-revision/lifecycle reads MUST
coalesce for all subscribers, so one subscriber leaving MUST NOT abort a request
still owned by another. When a non-cancellable mutation has already committed,
the Studio MUST reconcile that result into the originating project/Document
identity (or refresh it from the server) without applying it to the active
Document. Returning to that identity MUST use the committed revision or a newer
server revision as its baseline.

A deliberate Document switch MUST discard an edited local Draft that has not
been accepted and MUST NOT retain it as the inactive Document's client-side
state; before discarding, it MUST hand a non-conflicted Draft to the departing
Document's one rescue write, while an unresolved conflict Draft MUST NOT enter
the rescue path. Accepted server content — including a revision a rescue write
committed — MAY be recovered from the current-Document resource but MUST NOT
be described as Draft survival. A conflicted Draft remains available only while
its Document stays active or until the author chooses an explicit conflict
action. A rescue write MUST stay bound to the project and Document that own it:
it MUST NOT be issued for, write into, or publish state on a newly active
identity.

#### Scenario: Switching projects hides the previous aggregate immediately

- **GIVEN** project A is visible and project B starts loading
- **WHEN** the route project identity changes from A to B
- **THEN** project A and its actions are no longer rendered
- **AND** only project B may replace the loading state or publish a load error

#### Scenario: Late document completion is discarded

- **GIVEN** a save, rescue, restore, search, proposal, body, Lore-status, or beat request belongs to an earlier project, Document, revision, or intent
- **WHEN** it completes after the active ownership changed
- **THEN** its server result does not replace the active identity's Draft, accepted body, revision baseline, field value, result list, or error state
- **AND** a stale shell or body response does not replace current resource state
- **AND** a departure rescue write commits only on its originating Document and is never issued for, or applied to, the newly active identity

#### Scenario: A committed inactive-document mutation is reconciled

- **GIVEN** a save, a departure rescue write, a restore, or a proposal acceptance for Document A commits after the author selects Document B
- **WHEN** the author later returns to Document A
- **THEN** Document B was never overwritten by A's completion
- **AND** Document A reflects the committed server revision or a newer refreshed revision
- **AND** the next save for A uses that revision as its base

#### Scenario: An unpersisted draft does not survive document navigation

- **GIVEN** the author edits Document A and selects Document B before the save debounce elapses
- **WHEN** the author returns to Document A
- **THEN** A's unpersisted local Draft is absent as inactive client-side state rather than restored from it
- **AND** A loads its last accepted current revision, or the revision A's departure rescue write committed when that write was accepted
- **AND** B never displays or persists A's Draft

#### Scenario: An old export owner cannot trigger a download

- **GIVEN** an Export for project A is waiting for its artifact or download
- **WHEN** the route switches to project B or the workbench unmounts
- **THEN** every cancellable remaining request without another subscriber is aborted
- **AND** no catalog, error, pending state, object URL, or synthetic download from A is published into B

#### Scenario: A stale restore baseline remains recoverable

- **GIVEN** a revision restore uses a base revision that changed while its Document remains active
- **WHEN** the server rejects the restore with HTTP 409
- **THEN** the Studio retains the active local Draft and marks it conflicted
- **AND** refreshes the latest revision baseline without silently overwriting local text
- **AND** a subsequent explicit restore retry uses that refreshed base revision
