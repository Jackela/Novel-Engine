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
- Remove historical export snapshots that have no artifact or other evidence.

## Impact

- Affected application code: export artifact preparation, fresh export jobs,
  retry execution, and service wiring.
- Affected persistence code: the export outcome port/store and generated
  orphan-snapshot cleanup migration.
- Affected validation: transaction failure injection, filesystem compensation,
  source invalidation, fresh/retry API behavior, migration upgrade, and existing
  export format/download coverage.
