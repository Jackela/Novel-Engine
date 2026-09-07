## ADDED Requirements

### Requirement: Navigator document deletion

The Studio MUST offer a per-document delete command on each Navigator
document row. Because deletion is irreversible, the command MUST execute
only after an explicit confirmation step that names the document and
states that its unsaved Draft changes are lost; cancelling the
confirmation, including with the Escape key, MUST leave the document and
its Draft untouched. The command MUST be keyboard operable, announce its
pending state as deleting the named document, and return focus after
settling to the confirmation's trigger when the row survives or to a
surviving neighbor row when the row disappeared.

Deletion MUST remain document-level and server-authoritative: immutable
Revision and Snapshot semantics are unchanged, and when the server
refuses because the document is referenced by a snapshot, the refusal
MUST surface inline on the initiating row as a readable error with which
the author can retry or cancel. A successful deletion MUST remove only
that document's row from the project shell without reloading the shell;
when the deleted document was the active document, selection MUST fall
back to the route-compatible remaining document or the documented
no-document state, and the deleted document's local Draft MUST be
discarded.

#### Scenario: Confirmed deletion removes the document and falls back selection

- **GIVEN** a project with documents A (active) and B, and A holds unsaved Draft edits
- **WHEN** the author opens A's delete confirmation and confirms it
- **THEN** A disappears from the Navigator without a shell reload
- **AND** selection falls back to B and A's Draft is discarded
- **AND** focus lands on a surviving row in the same reading group

#### Scenario: Cancelled deletion leaves the document untouched

- **GIVEN** the author opened a document's delete confirmation
- **WHEN** the author cancels, including with the Escape key
- **THEN** the confirmation closes, the document and its unsaved Draft remain, and focus returns to the row's delete trigger

#### Scenario: Snapshot-referenced document refuses deletion inline

- **GIVEN** a document referenced by an existing snapshot
- **WHEN** the author confirms its deletion
- **THEN** the server refuses and the document remains in the Navigator
- **AND** the refusal renders inline on the initiating row as a readable error
- **AND** confirming again retries the command

#### Scenario: Deletion reports busy under the shared mutation group

- **GIVEN** a delete command is in flight for document A
- **WHEN** the Navigator renders during the request
- **THEN** the confirmation announces deleting A
- **AND** every other document mutation command in the Navigator is disabled without busy naming

### Requirement: Navigator chapter volume placement

The Studio MUST offer, on each Navigator chapter row of a project with
more than one volume, a placement control that issues the chapter's
volume placement for any volume other than the chapter's current one.
The control MUST be keyboard operable, never offer the current volume as
a target, and return to a neutral placeholder after issuing the command.

A successful placement MUST apply the server's complete Document response
causally to the project shell without a shell reload: only the summary
fields the command owns — volume, position, and updated timestamp — MAY
change for that document, and only while the revision captured when the
command was issued still owns the shell row and the command is still the
document's latest placement intent. A response outrun by a newer revision
or a newer placement intent MUST be ignored rather than overwrite newer
authority. Failures, including the permanent full-volume capacity
refusal and network failures, MUST surface inline on the initiating row
with the error envelope's message and capacity details, and re-issuing
the command MUST be the retry.

#### Scenario: Placing a chapter moves it to the target volume's tail

- **GIVEN** a project with volumes One and Two, and chapter C sits in One
- **WHEN** the author places C into Two through its Navigator row
- **THEN** C renders inside Two's group at the tail without a shell reload
- **AND** the placement survives a reload

#### Scenario: The current volume is never a placement target

- **GIVEN** a chapter currently in volume One of a two-volume project
- **WHEN** its placement control renders
- **THEN** volume One is not offered as a target and only volume Two can be chosen

#### Scenario: A late placement response cannot overwrite newer authority

- **GIVEN** a placement for chapter C is in flight
- **WHEN** a newer save advances C's revision, or a newer placement intent for C supersedes it, before its response settles
- **THEN** the older response is ignored
- **AND** the shell keeps the newer revision and placement authority

#### Scenario: Full-volume capacity refusal surfaces inline

- **GIVEN** the target volume is at its chapter capacity
- **WHEN** the author places a chapter into it
- **THEN** the chapter stays in its current volume
- **AND** the permanent capacity refusal renders inline on the initiating row naming the bounded resource and its limit
- **AND** placing into another volume remains possible
