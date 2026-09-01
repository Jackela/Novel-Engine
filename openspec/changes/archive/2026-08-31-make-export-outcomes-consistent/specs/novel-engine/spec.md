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

### Requirement: Project-scoped export artifacts
Export files MUST live under the project-scoped directory
`data/exports/<project_id>/` named by export id, and each export record MUST
capture its canonical file path, byte size, and SHA-256 checksum. Before the
database outcome commits, the filesystem MUST durably retain a unique stage
file and versioned publication manifest. After both files are durable and
before exposing the final, the system MUST persist a write-ahead cleanup intent
containing the complete manifest and the exact stage/manifest device and inode
identities without numeric precision loss. It MUST then expose the complete
final through a no-clobber atomic link and MUST fsync the owning directories.
The cleanup intent MUST authorize cleanup only for those identities and MUST
NOT count as a completed artifact; the database artifact row remains the commit
marker and discovery authority. Normal acknowledgement MUST remove the stage
and manifest only after a fully synchronized commit and only while their
captured identities still match, then clear the cleanup intent. Publication
failure MUST NOT unlink a stage, manifest, or manifest temporary that the
current attempt did not create, and replacements MUST be preserved. The
cleanup intent MUST remain until managed files converge. A crash or
acknowledgement failure MUST be
reconciled once after migrations and before job-state recovery or request
traffic.
Compensation MUST fsync the owning directory immediately after quarantining a
final path and before treating that quarantine as durable recovery evidence.

The process MUST acquire exclusive, OS-enforced ownership of the data directory
before backup, migration, reconciliation, or traffic and MUST hold ownership
until its database closes. A competing API or maintenance process MUST fail
before mutating backup, database, job, or export state. Ownership MUST be
released automatically on process death and MUST NOT introduce a job lease,
heartbeat, TTL, or stale-lock deletion protocol.

Pre-serve reconciliation MUST use database authority and integrity evidence:
an uncommitted final/stage/manifest set MUST be removed only when a matching
cleanup intent and inode/integrity evidence prove ownership. A parseable
manifest without that write-ahead intent MUST be preserved and MUST fail
startup. Committed valid files MUST be kept, a missing committed final MUST be
restored from a valid stage, and committed missing or mismatched evidence MUST
fail startup without deleting audit rows. A `.rollback-*` quarantine whose
cleanup intent plus stage/manifest proves the same inode and integrity evidence
MAY be removed; without that proof it MUST be preserved and MUST fail startup
for operator recovery. Cleanup intents MUST be cleared only after their file
state has converged.
Canonical-looking final files and legacy temporary files without a matching
manifest/stage ownership proof MUST likewise be preserved and MUST fail
startup; their names alone MUST NOT authorize deletion.
Stage-only files and staging temporaries without either committed database
integrity evidence or a parsed manifest hard-link identity MUST also be
preserved and MUST fail startup. A manifest without a stage, final, or matching
database artifact is likewise unproven and MUST be preserved.
This pass MUST be idempotent, confined to the real data root, and MUST reject
symlink or path-escape evidence. It is not scheduled cleanup of live projects;
the system MUST NOT run such scheduled cleanup.

Project deletion MUST acquire project-exclusive in-process ownership. If any
project pipeline is active, deletion MUST return 409 without deleting database
or filesystem state; while deletion holds ownership, new project pipelines MUST
also return 409 before project-row resolution. A proposal remains active until
its request-scoped provider cleanup finishes, for both synchronous and streaming
delivery. The database cascade is the successful deletion boundary.
Confined filesystem cleanup MUST run after commit; its failure MUST be reported
without changing the 204 response, and the next pre-serve reconciliation MUST
remove a directory whose project row and committed artifact evidence no longer
exist. If an artifact commit marker still references a missing project row,
startup MUST preserve the directory and fail closed. Export downloads MUST
resolve strictly within the data root.

#### Scenario: Atomic project-scoped write
- **GIVEN** an export request
- **WHEN** its file reaches the final artifact path
- **THEN** the path exposes only complete bytes at `data/exports/<project_id>/<export_id>.<ext>`
- **AND** durable stage and manifest evidence can reconstruct every pre-acknowledgement crash window

#### Scenario: File commit without database commit is removed at restart
- **GIVEN** final, stage, and manifest files exist but no artifact row committed
- **AND** a cleanup intent records the exact stage and manifest identities
- **WHEN** the next startup reconciles before serving
- **THEN** those uncommitted managed files are removed
- **AND** the cleanup intent is cleared only after removal converges
- **AND** no artifact or job evidence is fabricated

#### Scenario: Pre-intent crash is preserved
- **GIVEN** a stage or manifest became durable before its cleanup intent committed
- **WHEN** the next startup reconciles before serving
- **THEN** startup preserves the unproven files and fails for operator recovery
- **AND** a parseable manifest or canonical filename alone does not authorize deletion

#### Scenario: Database commit before acknowledgement is preserved
- **GIVEN** an artifact row and valid final file committed but stage and manifest cleanup did not run
- **WHEN** the next startup reconciles
- **THEN** the final file and all database evidence remain
- **AND** the recovery sidecars are removed

#### Scenario: Missing committed final is restored
- **GIVEN** an artifact row and valid durable stage exist but the final path is missing
- **WHEN** the next startup reconciles
- **THEN** the final path is restored from the verified stage before serving

#### Scenario: Missing committed evidence fails closed
- **GIVEN** an artifact row whose final and stage bytes are missing or disagree with recorded integrity evidence
- **WHEN** the server starts
- **THEN** startup fails before accepting traffic
- **AND** the artifact, snapshot, job, and event audit rows remain unchanged

#### Scenario: Rollback preserves replacements
- **GIVEN** a database publication failure and another writer has replaced the final path
- **WHEN** compensation runs
- **THEN** compensation does not unlink or overwrite the replacement
- **AND** any cleanup failure is reported without masking the database failure

#### Scenario: Sidecar name collision preserves prior bytes
- **GIVEN** a stage, manifest, or manifest-temporary path already exists
- **WHEN** a publication attempt receives an exclusive-create or no-clobber collision
- **THEN** failure cleanup preserves the prior path and bytes
- **AND** only sidecars whose captured device/inode identity belongs to the attempt may be removed

#### Scenario: Crash during rollback preserves an ambiguous quarantine
- **GIVEN** compensation moved the current final path to `.rollback-*` and the process stopped before proving its identity
- **WHEN** the next startup reconciles
- **THEN** startup preserves the quarantine and fails before accepting traffic
- **AND** no possible replacement bytes are deleted automatically

#### Scenario: Proven publication quarantine is reconciled
- **GIVEN** rollback stopped after moving the publication final to `.rollback-*`
- **AND** a cleanup intent, valid manifest, and stage prove the quarantine is the same publication inode and bytes
- **WHEN** the next startup reconciles
- **THEN** the managed quarantine and uncommitted publication sidecars are removed

#### Scenario: Final-only bytes are not proof of ownership
- **GIVEN** a live project export directory contains a canonical-looking final or legacy temporary file
- **AND** no valid manifest/stage inode and integrity evidence proves ownership
- **WHEN** startup reconciliation examines the directory
- **THEN** startup preserves the file and fails before accepting traffic

#### Scenario: Staging names are not proof of ownership
- **GIVEN** a live project's staging directory contains a stage-only file, temporary, or manifest-only file
- **AND** no committed artifact evidence or parsed manifest hard-link proves ownership
- **WHEN** startup reconciliation examines the staging directory
- **THEN** startup preserves the file and fails before accepting traffic

#### Scenario: A second process cannot race startup or publication
- **GIVEN** one API or maintenance process owns a data directory
- **WHEN** another process tries to open the same data directory
- **THEN** the second process fails before backup or reconciliation mutates state
- **AND** after the first database closes or its process dies, a later process may acquire ownership

#### Scenario: Project deletion is exclusive
- **GIVEN** an export, review, or proposal is active for a project
- **WHEN** deletion is requested for that project
- **THEN** deletion returns 409 and the project remains intact
- **AND** after the active work finishes, deletion may acquire exclusive ownership

#### Scenario: Deletion ownership rejects every arriving pipeline
- **GIVEN** project deletion committed its database cascade and post-commit cleanup is still active
- **WHEN** an export, review, retry, synchronous proposal, or streaming proposal arrives
- **THEN** the new pipeline returns 409 for project deletion rather than 404

#### Scenario: Proposal cleanup remains inside the active lifetime
- **GIVEN** a synchronous or streaming proposal landed its terminal outcome
- **AND** its request-scoped provider cleanup has not finished
- **WHEN** project deletion is requested
- **THEN** deletion returns 409 until provider cleanup finishes

#### Scenario: Project deletion removes exports
- **GIVEN** a project with completed exports and no active project pipeline
- **WHEN** the project is deleted
- **THEN** the project's database rows commit their deletion atomically
- **AND** its export directory is removed before the exclusive guard is released, or by the next startup after a reported cleanup failure

#### Scenario: Post-commit cleanup failure converges
- **GIVEN** the project database cascade committed and export-directory removal fails
- **WHEN** deletion responds and the process later restarts
- **THEN** deletion responds 204 and reports the cleanup failure once
- **AND** pre-serve reconciliation removes the ownerless project directory

#### Scenario: Contradictory database evidence is preserved
- **GIVEN** an artifact commit marker references a project row that is missing
- **WHEN** startup reconciliation finds that project's export directory
- **THEN** startup preserves the directory and committed bytes
- **AND** startup fails before accepting traffic

#### Scenario: Downloads cannot escape the data root
- **GIVEN** an export path or project export leaf is a symlink or path-escape attempt
- **WHEN** download, deletion, or startup reconciliation examines it
- **THEN** no file outside the configured data root is read or deleted

#### Scenario: Project cleanup detects parent replacement
- **GIVEN** project deletion validated its export directory
- **WHEN** the export root or project leaf is replaced before recursive cleanup
- **THEN** cleanup fails closed before deleting the replacement tree
- **AND** no path outside the configured data root is recursively removed

### Requirement: Restart recovery without invented leases
On startup, every job left in the running state by a previous process MUST be
marked interrupted, MUST carry the fixed restart error, and MUST record a job
event naming the restart reason; the author MAY then explicitly retry such a
job. Job-state recovery MUST NOT introduce lease columns, leases with TTLs,
heartbeats, lease renewal, worker registration, or any background executor:
"lease" exists only as narrative wording inside payload-visible strings, and
jobs execute within the request lifecycle. The separate one-time pre-serve
export reconciliation MUST run before job-state recovery and MUST NOT create a
worker, lease, or scheduled cleanup path.

#### Scenario: Running job is interrupted at restart
- **GIVEN** a job is running when its process stops
- **WHEN** the next startup completes
- **THEN** the job reads as interrupted and carries the fixed restart error
- **AND** a job event records the restart reason
- **AND** the author can explicitly retry the job

#### Scenario: Recovery uses no lease machinery
- **GIVEN** the process stops at any point
- **WHEN** the next startup restores a consistent state
- **THEN** job-state recovery performs only startup-time row updates and event inserts
- **AND** export publication reconciliation is a bounded pre-serve pass
- **AND** no lease, heartbeat, renewal, worker-registration, or scheduled executor participates
