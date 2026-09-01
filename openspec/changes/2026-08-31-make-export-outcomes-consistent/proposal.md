# Change: Make export outcomes consistent

## Why

The export pipeline currently persists an export snapshot before rendering,
persists the artifact record after the file write, and only then records the
completed job. A renderer, persistence, or job-event failure can therefore
leave an unreferenced snapshot that blocks document deletion, an artifact with
no matching completed job, or a published file whose database outcome failed.

## What Changes

- Capture export source data without creating durable snapshot rows.
- Publish the rendered file first, then commit the export snapshot, artifact,
  and fresh completed job/event in one immediate SQLite transaction.
- Commit an export retry's snapshot, artifact, and completed transition/event in
  one immediate SQLite transaction.
- Revalidate the captured immutable source when the database outcome lands.
- Compensate a published file when database publication fails, while preserving
  and reporting the original failure.
- Reuse snapshots only when the complete ordered document projection matches,
  so title, metadata, kind, or reading-order changes cannot render stale bytes.
- Retain a durable staging file and publication manifest until the database
  commit marker exists, then reconcile every crash window before serving.
- Persist a write-ahead cleanup intent with lossless stage/manifest inode
  identities before the final link; clear it only after managed-file cleanup.
- Enforce one process-lifetime owner for a data directory before backup or
  reconciliation, and durably sync SQLite commit markers before removing file
  recovery evidence.
- Make project deletion exclusive with in-flight project work; treat database
  deletion as the success boundary and filesystem removal as reported,
  restart-recoverable cleanup.
- Remove historical export snapshots that have no artifact or other evidence.

## Impact

- Affected application code: export artifact preparation, fresh export jobs,
  retry execution, project deletion, in-flight coordination, and service wiring.
- Affected persistence code: the export outcome port/store, generated
  orphan-snapshot cleanup migration, and generated publication-cleanup-intent
  migration.
- Affected startup/filesystem code: durable publication, pre-serve
  reconciliation, confined project cleanup, and database lifecycle ordering.
- Affected validation: transaction failure injection, filesystem compensation,
  crash-window restart fixtures, source ordering, concurrent deletion,
  migration upgrade, and existing export format/download coverage.
