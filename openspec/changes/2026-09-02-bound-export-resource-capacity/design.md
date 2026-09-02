# Design: bounded export resource lifecycle

## Existing boundary and retained identity work

Export currently captures every document and revision as strings, derives a
second chapter projection, lets Markdown, DOCX, or EPUB produce one complete
Buffer, and passes that Buffer through publication. Download reads an entire
file before checking its recorded size and checksum. Rollback and startup
recovery can reread whole stage, final, quarantine, and manifest files while
other copies remain live. The expensive-workflow guard limits export request
count but not renderer memory, and downloads consume no byte capacity.

The active `bound-export-source-revalidation` change already keeps every
source-identity query below the SQLite binding ceiling and validates all groups
inside one `IMMEDIATE` landing transaction. This change preserves that work and
the immutable snapshot/revalidation decision. It bounds the allocations around
that decision; it does not replace grouped revalidation or weaken compound
project/document/revision ownership and cardinality checks.

## Fixed budgets and measurement

One immutable application policy owns these limits:

| Resource | Inclusive limit | Measurement point |
|---|---:|---|
| `source_documents` | 65,536 | Every document in the ordered export projection, including non-chapters |
| `source_bytes` | 16,777,216 | Raw UTF-8 bytes of project title plus every document id, revision id, kind, title, content Markdown, and metadata JSON |
| `artifact_bytes` | 67,108,864 | Serialized Markdown, DOCX, or EPUB bytes and every stored/downloaded artifact |
| `manifest_bytes` | 16,384 | Raw publication-manifest bytes before UTF-8 decode or JSON parse |
| active renderers | 1 | One admitted source-capture/render/publication lifecycle per API app |
| download reservations | 134,217,728 | Sum of recorded artifact bytes held by active download responses per API app |

Numeric positions, timestamps, and fixed object overhead do not contribute to
`source_bytes`; every variable-length source string does. Source counts and byte
totals are computed by the persistence owner in the same read transaction that
captures the projection and before `.all()` or equivalent JavaScript
materialization. SQLite byte length, not JavaScript UTF-16 length or Unicode
code-point count, is authoritative. A bounded error reports `observed` as at
most `limit + 1`, so failure payload size cannot disclose or mirror the input.

Exact limits are accepted. No environment or request override can relax them.
The 16 MiB source decision is a deliberate export/import compatibility tradeoff:
the 64 MiB legacy-import ceiling protects a different source-reading boundary
and remains unchanged.

## Rendering and publication ownership

After authentication, schema checks, target conflict checks, and the existing
expensive-workflow admission, an export acquires the sole app-local renderer
permit before source capture. A retry acquires it before reserving or creating
its durable running retry Job. Unavailability returns the established 503
`OPERATION_CAPACITY_EXCEEDED` envelope with application scope, `limit: 1`,
`in_flight: 1`, and `Retry-After: 5`; it creates no Job, event, snapshot,
artifact, stage, manifest, final, or cleanup intent. The outer workflow still
releases its general permit.

The renderer permit spans source capture, chapter derivation, serialization,
publication landing, acknowledgement or rollback, and release of renderer-owned
Buffers. Release is opaque-token, generation-safe, and idempotent. The bounded
serializer or sink stops on the first byte beyond `artifact_bytes`; it never
publishes a truncated file. Markdown must avoid an additional unbounded joined
string, while DOCX and EPUB must use bounded output accumulation or a bounded
streaming sink. The existing byte-exact format contracts remain authoritative
for accepted output.

Source limits are checked before renderer construction. Artifact limits are
checked while output accumulates and again against the staged descriptor before
publication evidence is accepted. A permanent limit failure before publication
leaves no stage, manifest, final, cleanup intent, snapshot, artifact row, or
completed Job.

## Permanent fresh and keyed-retry outcomes

`ExportCapacityExceededError` owns the resources `source_documents`,
`source_bytes`, `artifact_bytes`, and `manifest_bytes`. HTTP maps it narrowly to
422 `EXPORT_CAPACITY_EXCEEDED`, message `Export capacity exceeded.`, and bounded
details `{ resource, limit, observed }`. OpenAPI declares that envelope on fresh
export, retry, and artifact-download routes. It is a definitive product result,
not an operational outage.

A fresh export capacity failure returns 422 and persists no Job or export
evidence. A keyed retry may discover a source, artifact, or generated-manifest
limit only after its durable running reservation. In that case one transaction
changes that exact
retry Job to `failed`, appends one failed event, and stores the structured
capacity resource, limit, and bounded observed value needed for HTTP replay.
The first response is 422. Replaying the same owner/project/source/key returns
the identical 422 envelope from the settled Job without executing, rendering,
adding events, or creating export evidence. This export-capacity exception is
more specific than the general terminal-retry 200 replay rule. A different key
is an explicit new attempt and may succeed after the project is reduced.

Renderer refusal occurs before a retry reservation and remains the existing
transient 503. It creates no failed Job or event, so the same key can be
replayed later. Download reservation is an independent read-only HTTP lifecycle
and never creates or settles a Job. Unexpected renderer defects, allocation
failures, and database/programming errors remain opaque 500 failures and are
not fabricated as capacity outcomes.

## Descriptor-owned reads, hashing, and recovery

Artifact readback opens the canonical final path with no-follow semantics and
uses the same descriptor for regular-file, device/inode, size, content, and
checksum validation. It rejects a recorded or observed size above
`artifact_bytes` before allocating the delivery Buffer. It allocates at most
the validated exact size, reads into that allocation with fixed chunks no
larger than 65,536 bytes, hashes the same chunks, and rejects early EOF,
truncation, or growth. Path replacement cannot redirect the open descriptor.

Rollback, acknowledgement, and startup recovery use the same bounded chunk
proof primitive but retain only identity, size, and SHA-256 evidence, not file
contents. They hash stage, final, and quarantine files sequentially with one
fixed scratch Buffer and do not keep two file bodies live. A manifest is
rejected from descriptor size at 16,385 bytes before allocation or parsing and
is rerejected if it grows while read.

An uncommitted stage, final, quarantine, or manifest that exceeds policy is
preserved and fails startup for operator recovery unless existing exact cleanup
authority proves it is safe to remove; capacity never broadens deletion
authority. A committed historical artifact larger than 64 MiB remains database
and catalog evidence and is verified incrementally without whole-file
allocation, but its download returns the stable 422. Recovery does not rewrite,
truncate, or silently bless it.

## Download reservation lifetime

After owner/project/artifact lookup and the permanent individual-size check,
the HTTP layer atomically reserves the artifact's recorded `size_bytes` against
the app-local 134,217,728-byte pool before filesystem allocation. An unavailable
reservation returns the existing application-scoped 503
`OPERATION_CAPACITY_EXCEEDED`, with the pool limit and current reserved bytes in
the established bounded numeric fields. It does not open or hash the file.

The reservation remains held through verification and until the response has
finished or closed, including client disconnect and send failure, because a
response may retain the Buffer after the service call returns. Its opaque token
releases exactly once and cannot release a later reservation. The reservation
counts one application-owned artifact Buffer; kernel/socket buffering remains
the HTTP runtime's bounded transport responsibility. Exact 64 MiB artifacts are
eligible, two can be held at the 128 MiB pool limit, and the next positive-byte
reservation is refused until release.

## Narrow failure mapping

Artifact gateway catch blocks classify only expected missing-path, unsafe
path/identity, and integrity-mismatch failures as the existing non-disclosing
404. `ExportCapacityExceededError` passes to 422; admission errors pass to 503;
unexpected filesystem errors such as `ENOMEM` and implementation defects pass
to the opaque 500 boundary. Known publication write failures keep their
existing audited failed-Job behavior and are not relabelled as capacity.

## Deferred work

This vertical slice intentionally leaves artifact-catalog database rows,
filesystem directory enumeration, and cleanup-journal/recovery enumeration
unpaginated. It also leaves the grouped source-revalidation result map intact
instead of comparing and discarding each 500-binding group immediately. Those
P2 allocations require separate contracts because they change discovery,
startup, or transaction orchestration independently of byte-safe artifact I/O.

## Options rejected

- Reusing the importer's 64 MiB source ceiling permits multiple renderer-side
  expansions large enough to defeat a practical single-process bound.
- Checking output or artifact size after `readFile`, `Buffer.concat`, or ZIP
  completion limits storage but not peak allocation.
- Counting only chapter content leaves non-chapter snapshot identity and large
  titles/metadata unbounded.
- Reusing workflow-count admission for downloads does not account for artifact
  size or response lifetime.
- Mapping every filesystem exception to 404 hides capacity defects and host
  failures, making retry policy and operations evidence unreliable.
- Paginating every catalog and recovery scan in this change would broaden a P1
  vertical slice into independent protocol and startup-order decisions.
