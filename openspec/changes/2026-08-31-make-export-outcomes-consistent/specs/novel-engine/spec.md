## MODIFIED Requirements

### Requirement: Snapshot-bound export with reuse
Exports MUST be rendered from one read-only captured source and MUST NOT persist
an export snapshot before rendering succeeds. The latest export-reason snapshot
MUST be reused if and only if its revision map equals the captured revision map
over all documents; any divergence MUST create a new snapshot (reason `export`).
When a revision-map match selects an existing snapshot, rendering MUST use that
snapshot's stored document projection so the file and snapshot cannot disagree.
Only chapter documents export; a project with zero chapters MUST be refused
export with 422. All formats exported from one state MUST contain the same
ordered chapter revisions, and each completed export MUST record its snapshot.

On fresh success, source revalidation, snapshot reuse or creation, snapshot
documents, artifact metadata, the completed job, and its completed event MUST
commit in one immediate database transaction. On retry success, the same export
evidence and the running retry's completed transition/event MUST commit in one
immediate transaction. If database publication fails after file publication,
the newly published file MUST be removed by identity-aware compensation; cleanup
failure MUST be reported without masking the original error. A deleted captured
source MUST NOT leave partial export evidence. An export retry MUST inherit the
original format but capture a fresh immutable source for that retry attempt; its
completed result MUST record that attempt's snapshot.

#### Scenario: Unchanged project reuses the snapshot
- **GIVEN** an export just completed
- **WHEN** another export is requested without any document change
- **THEN** both exports record the same snapshot id

#### Scenario: Any divergence creates a new snapshot
- **GIVEN** an export just completed
- **WHEN** any document — chapter or not — is saved or added, and another export is requested
- **THEN** a new snapshot with reason `export` is created and recorded

#### Scenario: Export without chapters is refused
- **GIVEN** a project contains only outline documents
- **WHEN** an export is requested
- **THEN** the response is 422 under the unified error envelope
- **AND** no export file, snapshot, artifact record, or job is created

#### Scenario: Formats agree on content
- **GIVEN** a project with several chapters
- **WHEN** markdown, DOCX, and EPUB exports are requested in the same state
- **THEN** all three carry the same ordered chapter revisions from one snapshot

#### Scenario: Fresh export completion is one outcome
- **GIVEN** a rendered export file from a valid captured source
- **WHEN** any snapshot, artifact, completed-job, or completed-event write fails
- **THEN** none of those database writes commit
- **AND** the newly published file is compensated without replacing the failure

#### Scenario: Retry export completion is one outcome
- **GIVEN** a running export retry and a rendered file from a valid source
- **WHEN** its terminal database transition fails
- **THEN** no new snapshot or artifact record commits
- **AND** the retry remains running for restart recovery
- **AND** the newly published file is compensated

#### Scenario: Concurrent source deletion is failure-closed
- **GIVEN** an export source is captured and one captured document is deleted before publication lands
- **WHEN** the rendered outcome is finalized
- **THEN** no partial snapshot or artifact evidence commits
- **AND** a fresh request records a failed export job if the project still exists

#### Scenario: Known publication failure is audited
- **GIVEN** the artifact filesystem reports a classified operational write failure
- **WHEN** a fresh export or export retry runs
- **THEN** the request reports a failed terminal job with the stable publication error
- **AND** no export snapshot, artifact record, or completed file is published

#### Scenario: Unexpected export defect remains visible
- **GIVEN** rendering or persistence raises an unclassified programming error
- **WHEN** the export request fails
- **THEN** the error remains an opaque server failure rather than a fabricated failed job
- **AND** no partial export database evidence or completed file remains

#### Scenario: Upgrade removes only orphan export snapshots
- **GIVEN** an earlier release left an `export` snapshot with no artifact
- **WHEN** the database upgrades through the generated migration channel
- **THEN** that snapshot and its snapshot-document rows are removed
- **AND** completed-export, review, and cross-snapshot review-issue evidence remains intact
