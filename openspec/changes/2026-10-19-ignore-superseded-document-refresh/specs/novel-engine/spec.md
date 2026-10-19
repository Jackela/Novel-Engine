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
request can fail, conflict, be cancelled, or lose its response. A 409 `REVISION_CONFLICT` MUST
retain the local Draft and a separate latest-server baseline while that
Document remains active. The active local Draft ends only by successful
acceptance, an explicit conflict choice that replaces it, a departure that
hands the newest text to its one rescue write, or a reload. A late save,
rescue, or conflict outcome MUST NOT publish into a newly active Document.

While the same selected Document still owns unaccepted Draft text or title,
the Studio MUST retain its unsaved-change close/refresh guard when the
accepted body is temporarily unavailable after an earlier save. A pending or
failed body reload MUST NOT be treated as proof that the Draft was saved.
The comparison MUST use the current owner's accepted text and title; returning
to that accepted content, explicitly discarding the Draft, or switching to a
clean owner MUST NOT leave a stale warning.

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

#### Scenario: A later local edit stays guarded during accepted-body reload

- **GIVEN** an autosave is in flight and the author makes a newer local edit
- **WHEN** the earlier save succeeds and the subsequent accepted-body read is pending or fails
- **THEN** the same owner's latest Draft remains protected by the unsaved-change close/refresh guard
- **AND** saved-source Review and Export guidance continues to identify unaccepted chapter edits
- **WHEN** the author restores the accepted content or explicitly discards the Draft
- **THEN** the stale warning is removed without retaining an inactive Draft

An explicit conflict reload MUST discard only the Draft covered by that author
choice. If the author edits the active Document's text or title while the
reload is pending, its response MUST preserve those newer edits as a conflict
against the returned accepted revision. Without a newer edit, the reload MUST
still replace the earlier Draft and settle as saved.

#### Scenario: Editing while a conflict reload is pending

- **GIVEN** the active Document has a revision conflict and the author chooses to load the latest version, discarding the earlier Draft
- **WHEN** the author edits its text or title before the latest-version response arrives
- **THEN** the response preserves the newer local text and title as an editable conflict
- **AND** a subsequent explicit keep-local save uses the returned accepted revision as its base

#### Scenario: A conflict reload without newer edits still discards

- **GIVEN** the author chooses to load the latest version of the conflicted active Document
- **WHEN** the latest-version response arrives without any subsequent local edit
- **THEN** the editor replaces the earlier Draft with the accepted text and title and settles as saved

If the same active Document accepts another Revision while a latest-version
read is pending, that superseded read MUST NOT replace the later accepted
Revision, its project summary, or any Draft entered afterward.

#### Scenario: A later History restore supersedes a pending reload

- **GIVEN** a conflict reload of the active Document is pending
- **WHEN** the author confirms a History restore and that restore accepts a new Revision before the earlier read returns
- **THEN** the earlier read is ignored and the restored Revision remains the active baseline and project summary
- **AND** text or title entered after the restore remains editable and its next save uses the restored Revision as its base
- **AND** without a subsequent edit the restored Document stays saved without a spurious conflict
