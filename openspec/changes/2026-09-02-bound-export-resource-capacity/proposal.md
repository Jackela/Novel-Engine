# Bound export resource capacity

## Why

Export source identity is now revalidated safely beyond SQLite's variable
limit, but the surrounding resource lifecycle still materializes unbounded
document projections, renderer output, artifact reads, rollback evidence, and
recovery proofs. A large project or artifact can therefore create several
simultaneous copies in the Node process, while concurrent downloads bypass the
existing expensive-workflow admission guard entirely.

## What Changes

- Apply fixed export limits before large allocations: 65,536 source documents,
  16,777,216 raw source bytes, 67,108,864 artifact bytes, and 16,384 publication
  manifest bytes. Exact limits are accepted; the first byte or document beyond
  them is rejected.
- Admit at most one active renderer per API app and reserve at most 134,217,728
  artifact-download bytes per app. Both refusals reuse the existing transient
  503 `OPERATION_CAPACITY_EXCEEDED` response and never queue work.
- Bound serialization, descriptor-owned artifact reads, incremental hashing,
  rollback, and startup recovery so artifact and proof verification cannot
  silently fall back to whole-file duplicate buffers.
- Return stable 422 `EXPORT_CAPACITY_EXCEEDED` for permanent fresh-export,
  keyed-retry, and download limit failures. Persist and replay an export retry's
  definitive capacity failure without rendering or creating a second attempt.
- Narrow filesystem catch boundaries so only classified absence, unsafe
  identity, or integrity failures become the existing non-disclosing 404;
  capacity, transient admission, unexpected I/O, and programming failures keep
  their own classifications.

## Impact

- Changes export source capture, renderers, artifact publication/readback,
  download response lifetime, retry landing/replay, recovery, error/OpenAPI
  contracts, generated frontend types, and the error catalog.
- The 16 MiB export-source ceiling is deliberately lower than the legacy
  importer's 64 MiB workspace ceiling. A valid imported project between those
  bounds remains readable and editable but cannot be exported until reduced;
  import compatibility and its existing limit do not change.
- Existing committed artifacts above 64 MiB remain catalogued and are verified
  incrementally during recovery, but download is refused with the new 422.
- Adds no dependency, migration, asynchronous worker, queue, or configurable
  unlimited override. Successful response shapes and exact export formats do
  not change.

## Non-goals

- No pagination of artifact catalog queries, filesystem recovery enumeration,
  or cleanup-journal enumeration; those are a separate later capacity change.
- No replacement of the existing 500-binding export-source revalidation and no
  immediate compare-and-discard rewrite for its accumulated result map; that
  P2 optimization remains a later change.
- No streaming download protocol, range requests, external object store,
  distributed semaphore, dynamic tuning, or background render queue.
- No change to legacy-import, document-edit, or AI-provider size policy.

## Validation

- Exact and plus-one tests for every source-document, source-byte, artifact-byte,
  and manifest-byte boundary, including UTF-8 byte counting and sparse files.
- Renderer and download admission races proving one renderer, 128 MiB of held
  download reservations, exact-once release, and zero-side-effect 503 refusal.
- Fresh and keyed-retry tests proving stable 422 evidence/replay, different-key
  recovery after source reduction, and no snapshot/artifact/file on refusal.
- Descriptor growth, truncation, replacement, rollback, restart recovery, and
  narrow error-mapping tests, followed by OpenAPI drift, server gates, strict
  OpenSpec, and fixed-SHA evidence.
