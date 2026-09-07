# Design: bounded descriptor-owned legacy reads

## Accepted budgets

The reader owns one fixed policy rather than exposing new environment knobs:

- `story.yaml`: at most 262,144 bytes;
- each `chapter-*.md`: at most 4,194,304 bytes;
- story plus accepted chapters: at most 67,108,864 bytes;
- accepted chapters: at most 2,000;
- entries observed in `manuscript/chapters`: at most 4,096.

The per-chapter ceiling accommodates the product's one-million-code-point
proposal ceiling even when every code point requires four UTF-8 bytes. The
workspace ceiling permits a large novel while keeping the worst accepted
Buffer/string projection finite. Chapter and scan ceilings also bound work for
empty files and non-matching directory entries, which a byte budget alone does
not constrain. Limits count raw bytes before UTF-8 decoding; exact limits are
accepted and the next byte or entry is rejected.

## File identity and confinement

The reader captures the canonical source and relevant directory identities.
It opens each file with `O_RDONLY | O_NOFOLLOW`, validates a regular file with
`FileHandle.stat`, and performs every bounded read through that same handle.
It then resolves the current path, requires the expected canonical parent, and
compares device/inode identity with the open handle. A final directory identity
check rejects an observable source, manuscript, or chapters replacement.

This order prevents a final-component link from being followed and prevents a
parent-directory replacement from authorizing an outside handle: an outside
real path fails confinement, while a path restored to an inside file cannot
match the already-opened outside inode. Once validated, later path changes do
not affect bytes read from the pinned handle. Expected missing/link/change
conditions become explicit legacy-source operation failures; unexpected I/O or
programming defects remain visible.

Node does not expose a portable `openat` directory-fd API. The contract
therefore promises pinned accepted files plus rejection of observable directory
identity changes, not a filesystem-wide atomic snapshot under a privileged
writer that continually replaces and restores every path.

## Bounded asynchronous traversal

`opendir` yields entries incrementally. The reader increments the scan count
before filtering names, stops at 4,097, and closes the iterator on every path.
Matching names are collected only through the 2,000 chapter ceiling, then
sorted with the existing lexical comparator. Each sorted file is opened and
read in bounded chunks; the implementation rejects from `fstat.size` before
allocation and also enforces the running byte count while reading so a file
that grows after `fstat` cannot exceed policy.

Hashing uses the exact accepted byte buffers and existing relative-path order.
The source is never written. The bounded set is returned only after all file
and directory checks pass, so preview and import cannot observe a partial
workspace.

## Application and error boundary

The `LegacyWorkspaceReader` port returns promises. `ImportService` preview and
import methods await the complete read before store access. The Fastify route
uses the existing asynchronous studio error mapping; the CLI already awaits
its import runner. Store writes remain one transaction and the owner/source-hash
unique index remains the idempotency authority.

Budget failures use `ImportCapacityExceededError` and map to HTTP 422 with code
`IMPORT_CAPACITY_EXCEEDED` and bounded details `{ resource, limit, observed }`.
The resource is one of `story_bytes`, `chapter_bytes`, `workspace_bytes`,
`chapter_count`, or `directory_entries`. The CLI reports the same failure and
exits 1; there is no force or unlimited override. Link and observable
source-change failures retain explicit invalid-operation handling, and a
missing confined workspace remains the existing 404. Unexpected I/O, resource,
and programming failures are not swallowed or normalized as invalid input.

Successful CLI import emits a `LegacyImportResult` summary containing only
project id, title, description, import hash, chapter count, and a `created`
boolean. It never serializes imported document bodies, so output size is bounded
independently of chapter Markdown. `created: false` is the explicit idempotent
reuse signal.

## Options rejected

- Checking size after `readFile` does not bound the allocation peak.
- `lstat` followed by path-based `readFile` retains the replacement race.
- A byte limit without entry and chapter limits leaves unbounded directory and
  empty-file work.
- A synchronous reader inside a worker would avoid event-loop blocking but add
  a new runtime/protocol boundary while still requiring descriptor identity and
  byte budgets.
- Silently truncating or skipping files would change the source hash and import
  meaning; the reader fails the whole workspace instead.
