# Bound export source revalidation

## Why

Export publication revalidates every captured revision before it commits the
snapshot, artifact, Job, and event. The current persistence query binds the
complete revision collection in one SQLite statement. This host permits 32,766
bound variables, while that statement also binds the project id, so a valid
project with 32,766 documents crosses the database limit and turns export into
an opaque 500 after rendering has already completed.

This is an implementation-size failure, not a stale-source outcome. Export must
continue validating the complete captured source at every supported project
size without truncating documents or weakening the atomic publication boundary.

## What Changes

- Revalidate every captured document/revision identity and its immutable
  content and metadata without making one SQL statement proportional to the
  complete project size.
- Keep all bounded reads and the aggregate exact-source decision inside the
  same immediate publication transaction.
- Reject missing or wrongly scoped captured identities through the existing
  source-invalidated behavior. Keep duplicate captured identities and mutation
  of persisted immutable content as visible invariant defects; do not silently
  collapse or normalize them into expected operational failures.
- Preserve the existing no-chapter behavior for an empty captured revision
  collection.
- Add production-path regressions at 32,765, 32,766, and 32,767 captured
  revisions, plus empty and duplicate collections.

## Impact

- Changes only export-source revalidation internals and their focused store and
  application regression coverage.
- Does not change HTTP shapes, database schema, migrations, artifact names,
  snapshot reuse rules, file formats, or the public error vocabulary.
- Preserves the existing file-first publication protocol, identity-aware
  compensation, and single-transaction database outcome.

## Non-goals

- No document truncation, sampled validation, partial snapshot, or
  best-effort export.
- No transaction per batch, concurrent source mutation window, asynchronous
  export worker, artifact-size policy, retention policy, or download change.
- No new index or migration unless production query-plan evidence proves one is
  necessary; none is expected for the bounded primary-key revision lookups.

## Validation

- Store-level red/green tests exercise the same query path used by production,
  not copied SQL or an isolated placeholder-count approximation.
- Boundary fixtures prove exact behavior for 32,765, 32,766, and 32,767
  captured revisions, including a valid chapter and the complete ordered
  projection.
- Empty, duplicate, deleted, wrongly scoped, and immutably changed revision
  collections prove the established no-chapter, invalidation, fail-loud,
  compensation, and zero-partial-evidence behavior.
- Relevant export, retry, transaction, publication cleanup, type, architecture,
  size, and strict OpenSpec gates run before archival.
