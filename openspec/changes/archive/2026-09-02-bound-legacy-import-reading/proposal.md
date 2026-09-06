# Bound and pin legacy workspace reads

## Why

The legacy reader checks a path with `lstat` and later reads that path again.
A concurrent replacement can therefore turn an accepted regular file into a
symbolic link before `readFile`, allowing the confined web preview to consume
bytes outside `data/imports`. The same reader synchronously loads every matching
chapter with no file, count, directory-scan, or total-byte budget; one owner
request can block the Node event loop and allocate several copies of an
arbitrarily large workspace.

## What Changes

- Make the legacy reader asynchronous and open every source file once with
  no-follow semantics; validate and read through that same file handle.
- Prove each opened file remains a regular file inside the captured workspace
  directories, and reject source or directory identity changes rather than
  accepting a mixed or escaped workspace.
- Apply fixed defensive budgets before decoding, hashing, preview response
  construction, or database mutation: 256 KiB for `story.yaml`, 4 MiB per
  chapter, 64 MiB for all accepted source files, 2,000 chapter files, and
  4,096 scanned chapter-directory entries.
- Iterate the chapter directory asynchronously and stop at the first exceeded
  budget; preserve filename ordering and the existing source hash for accepted
  workspaces.
- Carry the asynchronous boundary through web preview and CLI import while
  preserving idempotency and the all-or-nothing database transaction.
- Replace the CLI's unbounded full-project JSON with a stable import summary
  whose size does not grow with imported Markdown.

## Impact

- A workspace within every budget retains its existing project, chapter,
  preview, and hash semantics; CLI import reports the same result through a
  bounded summary.
- A changed, escaped, or oversized source fails with an explicit operation
  error before preview output or database work.
- No dependency, migration, frontend, or successful HTTP response-shape change
  is required.

## Non-goals

- No recursive workspace discovery or support for symbolic links.
- No background import queue, uploaded archive format, or new configuration
  surface.
- No change to document-edit limits, project/revision pagination, or export size
  policy.
- No claim of a cross-filesystem atomic snapshot; the reader pins each accepted
  file and rejects observable directory identity changes.

## Validation

- Deterministic replacement races for story, chapter, and workspace directory
  identities, proving no outside bytes are returned.
- Exact limit and limit-plus-one cases for every byte/count/scan budget,
  including multi-byte UTF-8 and many non-matching entries.
- Web preview proves prompt rejection, responsive event-loop behavior, stable
  envelopes, and zero database evidence.
- CLI and application regressions prove accepted import ordering, source-hash
  idempotency, transaction rollback, and bounded created/reused summaries.
- Full server gates, strict OpenSpec, and fixed-SHA evidence.
