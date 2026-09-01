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
snapshot. Reuse compares the complete ordered document projection directly:
document id, revision id, kind, title, content, metadata, position, and array
order. A match returns the snapshot's stored projection so rendered bytes
cannot disagree with the reused snapshot. Any difference, including a reorder
without a new revision, freezes the live projection and causes the later
landing to create a new snapshot. Direct equality keeps the existing snapshot
documents as the single source of truth; a persisted fingerprint was rejected
because it would be a second fact requiring its own migration and drift rules.
The artifact service validates that at least one chapter exists and renders
exactly the captured source.

### File-first publication with database authority

The gateway first writes and fsyncs a unique stage file, then writes a versioned
publication manifest and fsyncs the staging directory. After both identities
exist, it durably inserts a write-ahead cleanup-intent row containing the
manifest plus the exact stage and manifest device/inode values serialized as
decimal text. Only then does it no-clobber hard-link the stage to the final
artifact name and fsync the project directory. The cleanup intent authorizes
cleanup of those exact acquired inodes; it is not artifact discovery or proof
of a successful export. The stage, manifest, and cleanup intent remain durable
until the outcome is resolved and cleanup completes. Only after file
publication succeeds may the export outcome store run one immediate transaction
that:

1. revalidates every captured document/revision pair;
2. reuses the exact capture-selected snapshot or creates a snapshot from the
   captured projection;
3. validates and inserts the canonical artifact path, format, size, and
   checksum evidence; and
4. inserts the fresh completed job/event or completes the running retry/event.

The database artifact row is the commit marker and discovery authority. SQLite
uses `synchronous=FULL` so that marker is durable before filesystem recovery
evidence is removed. After commit, acknowledgement removes the exact stage and
manifest and then deletes the cleanup intent; acknowledgement failure is
reported but cannot reverse the committed outcome. If the transaction fails,
the application invokes identity-aware rollback and deletes the intent only
after all managed files converge. Rollback atomically quarantines the final
path, immediately fsyncs the owning directory, and only then verifies its inode
and bytes; it never unlinks a later replacement.
If rollback restores a replacement or cannot reach a durable verdict, it
retains stage, manifest, and cleanup-intent evidence and reports cleanup failure
separately without replacing the transaction failure.

Stage, manifest, and manifest-temporary cleanup follows the same ownership
rule. Exclusive creation/no-clobber success records bigint device/inode
identity for each acquired path. Failure, acknowledgement, and rollback clean
only matching identities through quarantine-and-verify; a pre-existing or
replaced path is restored or retained for startup/operator evidence. Cleanup
quarantine rotation first normalizes any prior cleanup suffix, so repeated
retries retain one bounded suffix instead of growing path names indefinitely.

### Pre-serve reconciliation

Startup first acquires a process-lifetime SQLite lock dedicated to the data
directory, then remains ordered: backup, migrations, export publication
reconciliation, job-state recovery, traffic, and finally lock release after
database close. A competing API or maintenance process fails before backup or
reconciliation. This is an OS-released ownership lock, not a job lease, TTL, or
heartbeat. Reconciliation is a one-time deterministic pass, not a scheduled
worker. SQLite separates cleanup authority from success authority:

- no artifact row plus a matching cleanup-intent row permits removal of only
  the recorded final/stage/manifest inodes;
- no artifact row and no cleanup intent preserves sidecars and fails startup,
  even when a manifest parses and its names look canonical;
- an artifact row plus valid final bytes keeps the final and removes sidecars;
- an artifact row plus a valid stage but missing final restores the final by
  hard link;
- an artifact row with missing or mismatched evidence fails startup without
  altering database audit rows;
- a project directory with no project row is removed after symlink and
  confinement checks.

The cleanup intent is cleared only after filesystem convergence. A crash after
manifest durability but before intent insertion is therefore deliberately
ambiguous: startup preserves the bytes for operator recovery rather than
promoting a manifest name into deletion authority.

A canonical-looking final or legacy temporary file in a live project is not
proof of ownership. Without a matching manifest/stage inode and integrity
evidence, reconciliation preserves it and fails closed for operator recovery.
The same rule applies inside `.staging`: a stage-only file requires committed
artifact integrity evidence, and a manifest temporary is removed only when it
is the same inode as a valid parsed manifest. Other temporaries are preserved
and stop startup. A manifest with no stage, final, or database commit marker is
also unproven and preserved.

A `.rollback-*` quarantine is deliberately different. Reconciliation removes
it only when a valid manifest/stage pair proves the quarantine is that exact
publication inode with matching integrity evidence. Otherwise it preserves the
quarantine and fails closed for operator recovery instead of deleting possible
replacement bytes.

The studio context owns this policy. Shared database startup exposes only an
after-migration/before-job-recovery hook and never imports a bounded context.

### Project-exclusive deletion

The application-level in-flight guard admits either ordinary project work or
one project-exclusive deletion. Deletion authorizes the principal before
consulting the guard, returns 409 while any project pipeline is active, and
blocks new pipelines until post-commit cleanup finishes. Authenticated proposal
requests enter the project guard after pure operation/provider admission but
before resolving project rows, so deletion ownership remains observable after
the cascade. Proposal ownership covers request-scoped provider disposal as well
as generation and outcome landing. The database cascade is the irreversible
success boundary. Confined filesystem cleanup runs after commit; failure is
reported once while the response remains 204, and the next startup removes the
now-ownerless directory only when no committed artifact row still references
it. Contradictory database evidence fails closed before any tree is removed.
The cleaner revalidates the export-root identity at the destructive boundary,
renames the checked project leaf to a private quarantine, and verifies the
quarantined inode before recursive removal. A detected parent or leaf
replacement fails closed. This avoids a false 500 after the database has
already deleted the project without letting corrupted authority authorize byte
deletion.

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
- **Persisted source hash:** direct comparison of the owned snapshot projection
  is collision-free, reviewable, and avoids a second persisted identity fact.
- **Delete filesystem inside the store:** the filesystem cannot join SQLite's
  transaction and could produce a 500 after an irreversible database commit.
- **Catch every export error as a failed job:** this would hide programming and
  persistence defects contrary to the repository's failure-visibility rules.
- **Scheduled cleanup for live projects:** periodic cleanup is still forbidden.
  The selected pre-serve pass reconstructs committed intent from the database
  artifact row and durable manifest before any request can race it.
