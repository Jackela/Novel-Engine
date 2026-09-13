## MODIFIED Requirements

### Requirement: Snapshot-bound export with reuse

Exports MUST be rendered from one read-only captured source and MUST NOT persist
an export snapshot before rendering succeeds. The latest export-reason snapshot
MUST be reused if and only if its complete ordered document projection equals
the captured projection over every document: document id, revision id, kind,
title, content, metadata, position, and array order. Any divergence, including
a reorder that creates no revision, MUST create a new snapshot (reason
`export`). When a projection match selects an existing snapshot, rendering MUST
use that snapshot's stored document projection so the file and snapshot cannot
disagree.
Only chapter documents export; a project with zero chapters MUST be refused
export with 422. All formats exported from one state MUST contain the same
ordered chapter revisions, and each completed export MUST record its snapshot.

Source revalidation MUST cover every captured document and revision regardless
of project document count. It MUST preserve the complete collection's
cardinality and MUST NOT truncate, sample, or silently deduplicate captured
identities. Empty captured sources MUST retain the existing no-chapter
behavior. A missing, wrongly paired, or wrongly scoped captured revision MUST
fail through the existing source-invalidated behavior. Duplicate captured
identities and mutation of persisted immutable content or metadata MUST remain
visible invariant defects rather than fabricated expected failures. None may
permit snapshot reuse or creation.

On fresh success, source revalidation, snapshot reuse or creation, snapshot
documents, artifact metadata, the completed job, and its completed event MUST
commit in one immediate database transaction. On retry success, the same export
evidence and the running retry's completed transition/event MUST commit in one
immediate transaction. The complete revalidation decision MUST occur inside
that same transaction regardless of collection size; no proper subset of the
source may commit or authorize publication. If database
publication fails after file publication, the newly published file MUST be
removed by identity-aware compensation; cleanup failure MUST be reported
without masking the original error. A deleted captured source MUST NOT leave
partial export evidence. An export retry MUST inherit the original format but
capture a fresh immutable source for that retry attempt; its completed result
MUST record that attempt's snapshot.

#### Scenario: Unchanged project reuses the snapshot

- **GIVEN** an export just completed
- **WHEN** another export is requested without any document change
- **THEN** both exports record the same snapshot id

#### Scenario: Any divergence creates a new snapshot

- **GIVEN** an export just completed
- **WHEN** any document — chapter or not — is saved or added, and another export is requested
- **THEN** a new snapshot with reason `export` is created and recorded

#### Scenario: Reading-order change creates a new snapshot

- **GIVEN** an export just completed for two chapters
- **WHEN** the chapters are reordered without creating a new revision
- **THEN** the next export records a new snapshot
- **AND** its rendered chapter order equals the captured reading order

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

#### Scenario: Export revalidates below the high-cardinality boundary

- **GIVEN** a valid captured source contains 32,765 distinct document revisions including a chapter
- **WHEN** the rendered export lands
- **THEN** every captured revision is revalidated and the export completes
- **AND** the recorded snapshot preserves the complete ordered projection

#### Scenario: Export revalidates at the high-cardinality boundary

- **GIVEN** a valid captured source contains 32,766 distinct document revisions including a chapter
- **WHEN** the rendered export lands
- **THEN** the export completes without a project-size-derived server failure
- **AND** every captured revision participates in one complete revalidation decision

#### Scenario: Export revalidates beyond the high-cardinality boundary

- **GIVEN** a valid captured source contains 32,767 distinct document revisions including a chapter
- **WHEN** the rendered export lands
- **THEN** the export completes without truncating or sampling the source
- **AND** its snapshot records the complete ordered projection

#### Scenario: A later bounded read invalidates the whole source

- **GIVEN** one captured revision outside the first bounded read is deleted or belongs to the wrong project or document after rendering
- **WHEN** the export source is revalidated
- **THEN** the existing source-invalidated outcome applies to the complete export
- **AND** no snapshot, artifact, completed job, or completed event commits
- **AND** the published file is compensated by the existing identity-aware protocol

#### Scenario: Duplicate captured identities fail loud and closed

- **GIVEN** a captured source repeats a document or revision identity
- **WHEN** the export source is revalidated
- **THEN** the duplicate is not collapsed into a smaller apparently valid collection
- **AND** it remains an opaque invariant failure rather than a fabricated failed Job
- **AND** zero partial database evidence commits

#### Scenario: Immutable source mutation remains visible

- **GIVEN** persisted content or metadata for a captured immutable revision differs during a later bounded read
- **WHEN** the export source is revalidated
- **THEN** the mismatch remains an opaque invariant failure rather than a source-invalidated outcome
- **AND** no snapshot, artifact, completed Job, or completed event commits

#### Scenario: Empty revision collection keeps no-chapter behavior

- **GIVEN** a captured source contains no document revisions
- **WHEN** export is requested
- **THEN** the existing no-chapter 422 response is returned
- **AND** no export file, snapshot, artifact record, or job is created
