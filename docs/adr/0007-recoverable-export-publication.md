# Recoverable export publication across SQLite and the filesystem

---
status: accepted
---

An export outcome crosses two authorities that cannot share one transaction:
SQLite owns discoverable snapshots, artifact metadata, jobs, and events; the
project export directory owns the bytes. Novel Engine therefore uses a
recoverable file-first protocol with SQLite as the commit marker. It does not
claim distributed or filesystem/database atomicity.

## Decision

### One captured source identity

Snapshot reuse compares the complete ordered snapshot-document projection
directly: document id, revision id, kind, title, content, metadata, position,
and array order. The stored snapshot projection is the owner; there is no
separate persisted fingerprint to migrate, collide, or drift. A reorder that
does not create a revision still changes identity and creates a new snapshot.

### Durable publication before database landing

For a new, unique artifact id, the filesystem adapter performs this sequence:

1. create a unique stage file with exclusive creation, write all bytes, and
   fsync the file;
2. create a versioned manifest containing project/artifact identity, format,
   canonical relative path, size, checksum, and stage name, then fsync the
   staging directory;
3. insert a durable cleanup-intent row containing the complete manifest and
   exact stage/manifest device and inode values serialized as decimal text;
4. no-clobber hard-link the stage inode to the final artifact name and fsync
   the project directory;
5. commit source revalidation, snapshot reuse/creation, validated canonical
   artifact metadata, and the fresh or retry job outcome/event in one immediate
   SQLite transaction using `synchronous=FULL`;
6. after SQLite commits, acknowledge publication by removing the stage and
   manifest, syncing their directories, and then clearing the cleanup intent.

The cleanup intent is write-ahead deletion authority for exact acquired inodes;
it is not artifact discovery or a successful outcome. The artifact row is the
commit marker. A database failure invokes compensation without replacing the
original error. Compensation first renames the final path to a unique
quarantine in the same directory and fsyncs that directory before verifying
the captured inode and bytes. It deletes only its own publication. A replacement is restored with a
no-clobber link. If it restored a replacement, or a newer path already exists,
the durable stage, manifest, and cleanup intent remain for startup/operator
evidence and cleanup failure is reported. The intent is cleared only after file
cleanup converges.

Sidecar ownership is captured at exclusive creation/link time as bigint
device/inode identity. Failure, acknowledgement, and rollback quarantine and
remove only that captured identity. An `EEXIST` path never acquired by the
attempt, or a later replacement at an acquired name, is preserved and
reported rather than unlinked by name.
Repeated cleanup retries normalize an existing cleanup suffix before choosing a
new quarantine, so a path cannot grow an unbounded suffix chain.

### Deterministic pre-serve reconciliation

Startup first acquires an OS-enforced, process-lifetime lock for the data
directory. Only the lock owner may run backup → migrations → export
reconciliation → running-job recovery → traffic. A competing API or maintenance
process fails before backup or reconciliation mutates shared state. The lock is
released only after the main database closes; process death releases SQLite's
file lock without a lease, TTL, or stale-lock cleanup protocol. Reconciliation
is one bounded startup pass, not a worker or scheduled cleanup loop.

| Artifact row | Matching cleanup intent | Valid final | Valid stage/manifest | Result |
|---|---:|---:|---:|---|
| absent | yes | either | present | remove only recorded uncommitted inodes, then clear intent |
| absent | no | either | present | preserve and fail for operator recovery |
| present | either | yes | present | keep final; remove proven sidecars |
| present | either | no | yes | restore final from stage; remove proven sidecars |
| present | either | yes | absent | verify and keep final |
| present | either | no/corrupt | no/corrupt | fail startup; preserve database evidence |

Every path is checked against the real data/export roots. Symlinks, malformed
manifests, non-canonical database paths, and integrity mismatches fail closed.
A real export directory whose project row and artifact rows no longer exist is
safe orphan state and is removed. If committed artifact evidence still names a
missing project, reconciliation preserves the tree and fails closed instead of
letting contradictory database state authorize deletion.

A final or legacy temporary file in a live project's export directory is not
owned merely because its name looks canonical. Without a matching durable
manifest/stage inode and integrity proof, startup preserves it and fails for
operator recovery rather than deleting possible replacement or user bytes.
Within `.staging`, a stage-only file is removable only against committed
artifact integrity evidence. A manifest temporary is removable only when its
inode is the parsed manifest's inode; every other temporary is preserved and
fails startup. A manifest without a stage, final, or matching artifact commit
marker is also preserved because its schema-valid contents are not ownership
proof by themselves.

A crash after manifest fsync but before cleanup-intent insertion is a deliberate
fail-closed gap: the final has not been linked, but startup does not infer
deletion authority from parseable metadata. It preserves the sidecars for
operator recovery. Journal rows are removed only after the corresponding file
state converges.

Rollback quarantines require an identity verdict. Startup may delete one only
when a valid manifest and stage prove the quarantine is the same inode with the
same size and checksum. If that proof is absent or disagrees, the quarantine,
replacement, and sidecars are preserved and startup fails closed for operator
recovery; deleting them automatically could destroy replacement bytes.

### Project deletion owns the whole project

Project deletion acquires the same process-local guard used by proposal,
review, and export work, but in project-exclusive mode. Active work makes
deletion return 409; deletion ownership makes newly arriving work return 409.
Principal authorization runs before the guard so activity cannot disclose
another owner's project. Authenticated proposal requests perform pure request
admission before entering the guard and resolve project rows only afterward,
so a committed deletion retains its 409 ownership throughout cleanup. Proposal
ownership is released only after request-scoped provider disposal completes.

The database cascade is the irreversible success boundary. Project export-tree
removal runs afterward through a confined, symlink-aware adapter. Cleanup
failure is reported once but does not turn a committed deletion into a false
500; startup reconciliation later removes the ownerless directory. Immediately
before recursion the adapter revalidates the export-root identity, quarantines
the checked project leaf under a private name, and verifies its inode. A
detected parent or leaf replacement fails closed.

## Consequences and limits

- Completed database evidence is atomic; crash windows in the file-first gap
  are replayable, removable from recorded intent, or deliberately preserved for
  operator recovery when write-ahead authority is absent.
- A missing or corrupt committed artifact prevents startup instead of silently
  rewriting history or fabricating a failed job.
- Acknowledgement and deletion cleanup are secondary, observable convergence
  work after their database commit markers.
- The data directory has enforced single-process ownership from before backup
  through database close. Node does not expose a portable
  `openat`/directory-fd API, so same-directory atomic operations, realpath
  confinement, no-follow leaf opens, and the independent SQLite lifetime lock
  form the local-storage boundary. Revisit this ADR before supporting multiple
  writers or remote/object storage.
- `synchronous=FULL` makes the SQLite commit marker durable before an
  acknowledgement or project deletion removes filesystem recovery evidence;
  a later WAL checkpoint is not the cross-authority durability boundary.
- Hard links and directory fsync must be supported by the configured local
  filesystem. An unsupported or cross-device setup fails publication rather
  than weakening the durability contract.

## Alternatives rejected

- **Database first, file second:** creates discoverable records whose bytes may
  never exist.
- **Best-effort temporary rename without intent metadata:** cannot distinguish
  committed bytes from crash orphans after restart.
- **Persisted source hash:** duplicates the owned projection and introduces
  versioning, collision, and migration concerns without improving equality.
- **Background cleanup worker or leases:** contradicts the synchronous job
  model and adds lifecycle machinery for a bounded startup decision.
- **Filesystem deletion inside the database store:** can return 500 after the
  project database rows have already committed their deletion.
