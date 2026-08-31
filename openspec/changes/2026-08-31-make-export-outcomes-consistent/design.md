# Design: Consistent export publication

## Context

An export outcome spans two authorities: SQLite owns discoverable snapshots,
artifact metadata, jobs, and events; the project-scoped filesystem owns the
artifact bytes. SQLite can make all database evidence atomic, but it cannot
enlist a filesystem rename in the same transaction.

## Decision

### Read-only source, then render

The export store exposes one read-only source capture containing the project
title and ordered document/revision payloads. Capturing the source creates no
snapshot. When the current revision map matches the latest reusable export
snapshot, capture returns that snapshot's stored projection (title, kind,
metadata, and order) so rendered bytes cannot disagree with the reused
snapshot. Otherwise capture freezes the live projection and the later landing
creates a new snapshot. The artifact service validates that at least one
chapter exists and renders exactly that captured source.

### File-first publication with database authority

The gateway publishes a complete, checksum-backed file under a new artifact id
and returns an identity-aware rollback capability. Only after that succeeds may
the export outcome store run one immediate transaction that:

1. revalidates every captured document/revision pair;
2. reuses the exact capture-selected snapshot or creates a snapshot from the
   captured projection;
3. inserts the artifact record; and
4. inserts the fresh completed job/event or completes the running retry/event.

The database record remains the discovery authority. If the transaction fails,
the application invokes the identity-aware rollback. A cleanup failure is
reported separately and never replaces the transaction failure.

### Failure classification

A captured source whose document or revision was deleted is an expected source
invalidation: a fresh request may record a failed export job if its project
still exists, and a retry transitions to failed. Persistence defects,
serialization defects, invalid job transitions, and violated immutable-source
invariants remain visible unexpected errors. They do not get converted into a
successful or ordinary failed outcome.

An export retry inherits the original command payload (its format) but captures
a fresh immutable source for that execution. Failed exports deliberately have
no durable snapshot to replay. Exact historical replay would require a separate
source-token decision and is not implied by the generic retry contract.

### Historical cleanup

The generated migration removes only `reason = 'export'` snapshots that have no
export artifact, review, or review-issue reference through one of their snapshot
documents. Cascading snapshot-document deletion releases historical deletion
blockers. Referenced export and review evidence is preserved.

## Alternatives Rejected

- **Database first, file second:** a file failure would leave a discoverable
  artifact whose bytes do not exist.
- **Independent artifact and job transactions:** this preserves the current
  audit split and cannot prove one completed outcome.
- **Catch every export error as a failed job:** this would hide programming and
  persistence defects contrary to the repository's failure-visibility rules.
- **Scheduled cleanup for live projects:** cleanup cannot reconstruct intent and
  is already forbidden by the product specification.
