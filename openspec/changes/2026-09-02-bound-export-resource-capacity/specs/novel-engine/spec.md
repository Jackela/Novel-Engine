## ADDED Requirements

### Requirement: Bounded export source and rendering

Every fresh or retry export MUST enforce one fixed inclusive policy before
unbounded JavaScript materialization: at most 65,536 documents in the complete
ordered export source and at most 16,777,216 raw UTF-8 source bytes. The byte
total MUST include project title and every document's document id, revision id,
kind, title, content Markdown, and metadata JSON; numeric positions and fixed
object overhead do not count. Non-chapter documents MUST count because they
remain part of snapshot identity. Count and byte measurement MUST occur in the
same persistence read transaction that captures the source and before loading
the complete projection into memory. Exact limits MUST be accepted and a
failure MUST report `observed` no greater than `limit + 1`.

Serialized Markdown, DOCX, or EPUB output MUST be at most 67,108,864 bytes.
Serialization MUST stop at the first byte above the limit, MUST NOT truncate,
and MUST NOT publish a stage, manifest, final, cleanup intent, snapshot,
artifact, completed Job, or completed event for rejected output. Accepted files
MUST retain the established byte and format contracts.

Each API app MUST admit at most one active export renderer. Its opaque permit
MUST be acquired before source capture and before a retry Job is reserved, MUST
span serialization, landing, acknowledgement or rollback, and renderer Buffer
release, and MUST release idempotently without allowing an old permit to
release a later owner. Refusal MUST return the existing application-scoped 503
`OPERATION_CAPACITY_EXCEEDED` with `limit: 1`, `in_flight: 1`, and
`Retry-After: 5`; it MUST NOT queue or create workflow evidence.

#### Scenario: Exact source limits are accepted

- **GIVEN** an export source has exactly 65,536 documents and exactly 16,777,216 counted UTF-8 bytes with at least one chapter
- **WHEN** a fresh or retry export captures it
- **THEN** source capacity permits rendering
- **AND** the complete ordered source remains subject to snapshot identity and revalidation

#### Scenario: Source document limit is exceeded

- **GIVEN** the complete ordered source contains 65,537 documents
- **WHEN** export source capture measures it
- **THEN** capture fails before the complete row projection is materialized
- **AND** the capacity details report `source_documents`, limit 65,536, and observed 65,537

#### Scenario: Source byte limit counts all variable strings

- **GIVEN** project title, ids, kind, document titles, Markdown, and metadata total 16,777,217 UTF-8 bytes across chapter and non-chapter documents
- **WHEN** export source capture measures it
- **THEN** capture fails before the complete row projection is materialized
- **AND** JavaScript UTF-16 length or Unicode code-point count cannot substitute for raw UTF-8 bytes

#### Scenario: Every format accepts the artifact boundary

- **GIVEN** bounded sources whose Markdown, DOCX, and EPUB serializers each produce exactly 67,108,864 bytes
- **WHEN** each format is exported
- **THEN** each exact artifact may proceed to durable publication
- **AND** its existing byte-exact format contract remains unchanged

#### Scenario: Renderer output crosses the boundary

- **GIVEN** a serializer reaches 67,108,865 output bytes
- **WHEN** it attempts to emit the next byte
- **THEN** serialization fails without truncation
- **AND** no export file, cleanup intent, snapshot, artifact row, or completed Job evidence is created

#### Scenario: A second renderer is refused before retry reservation

- **GIVEN** one API app already holds its renderer permit
- **WHEN** another fresh export or keyed export retry reaches renderer admission
- **THEN** it receives the existing 503 capacity envelope and retry header
- **AND** no source is captured and no running retry Job or first event is created

### Requirement: Export capacity failure protocol

A permanent export resource refusal MUST use HTTP 422 code
`EXPORT_CAPACITY_EXCEEDED`, message `Export capacity exceeded.`, and details
`{ resource, limit, observed }`. `resource` MUST be one of
`source_documents`, `source_bytes`, `artifact_bytes`, or `manifest_bytes`;
`limit` and `observed` MUST be safe non-negative integers and `observed` MUST be
bounded to at most `limit + 1`. The fresh export, keyed retry, and artifact
download OpenAPI contracts and generated frontend types MUST declare the
response. Unexpected allocation, renderer, filesystem, database, or programming
failures MUST NOT be normalized as this capacity error.

A fresh export capacity failure MUST create no Job or export evidence. When a
keyed export retry discovers a permanent source or artifact limit after its
running Job was reserved, it MUST atomically settle that Job as `failed`, append
exactly one failed event, and retain the structured capacity result required for
replay. The first request and every later replay of the same
owner/project/source/`Idempotency-Key` MUST return the identical 422 envelope;
replay MUST NOT execute work or add evidence. This specific definitive outcome
MUST override the general terminal-retry 200 replay rule. A different key MUST
remain an explicit new attempt. Transient renderer or download admission MUST
retain the existing 503 response, MUST occur before retry reservation, and MUST
allow the unresolved same key to be replayed later.

The export source limit is intentionally independent of the 67,108,864-byte
legacy-import workspace limit. Import MUST continue accepting a conforming
workspace that can create a project above the export-source limit; export MUST
fail closed until that project's counted source is within policy.

#### Scenario: Fresh permanent refusal has no evidence

- **GIVEN** a fresh export exceeds a source or artifact limit
- **WHEN** the request settles
- **THEN** it receives 422 `EXPORT_CAPACITY_EXCEEDED` with bounded resource, limit, and observed details
- **AND** no Job, event, snapshot, artifact, file, manifest, or cleanup intent exists for the attempt

#### Scenario: Keyed retry capacity failure is replayable

- **GIVEN** a keyed export retry reserved one running Job and then exceeded a permanent source or artifact limit
- **WHEN** the first response is returned and the same key is replayed after a lost response
- **THEN** both responses carry the identical 422 capacity envelope
- **AND** exactly one failed retry Job and failed event exist with no repeated render, snapshot, artifact, or file work

#### Scenario: A different key can try reduced source

- **GIVEN** one keyed export retry settled with a source-capacity failure and the author then reduces the project within policy
- **WHEN** the author explicitly retries the same source Job with a different key
- **THEN** the new key may create and execute a distinct retry Job under existing admission rules
- **AND** it is not replayed as the earlier capacity outcome

#### Scenario: Transient admission remains replayable

- **GIVEN** an export retry cannot acquire renderer or download-byte admission
- **WHEN** the author replays the same unresolved key after capacity is released
- **THEN** the earlier refusal remains the existing 503 rather than a terminal failed Job
- **AND** the replay may reserve and execute one retry attempt

#### Scenario: Import and export ceilings deliberately differ

- **GIVEN** a conforming legacy workspace is accepted under the 64 MiB import policy but produces more than 16 MiB of counted export source
- **WHEN** the imported project is read, edited, and then exported
- **THEN** import, reading, and editing remain valid
- **AND** export returns the stable permanent 422 until its counted source is reduced

### Requirement: Bounded export artifact proof and delivery

Every publication manifest MUST be at most 16,384 raw bytes and MUST be size
checked before UTF-8 decoding, allocation beyond that bound, or JSON parsing.
Every artifact stage, final, quarantine, recovery proof, and download MUST be
opened without following the final path as a symbolic link and MUST be checked
as a regular file through the same descriptor. Size, content, and SHA-256 proof
MUST use reads no larger than 65,536 bytes, reject growth, truncation, identity
replacement, and short reads, and MUST NOT retain multiple whole-file proof
Buffers. Artifact size MUST be checked against 67,108,864 before allocating a
delivery Buffer.

An oversized uncommitted recovery file MUST be preserved and fail closed unless
existing exact cleanup authority independently proves deletion safe. A
committed historical artifact above the new artifact limit MUST remain catalog
evidence and MUST be verified incrementally during recovery, but its download
MUST return 422 `EXPORT_CAPACITY_EXCEEDED`; recovery MUST NOT truncate, rewrite,
or fully buffer it.

Each API app MUST reserve the recorded artifact byte size before opening a file
for download and MUST cap the sum of active reservations at 134,217,728 bytes.
The reservation MUST remain owned through response finish, close, disconnect,
or send failure and MUST release exactly once with generation-safe ownership.
An individual artifact above 67,108,864 bytes is a permanent 422. A valid
individual artifact that cannot fit the current reservation pool MUST receive
the existing application-scoped 503 `OPERATION_CAPACITY_EXCEEDED` and
`Retry-After: 5` before file open.

Filesystem mapping MUST be narrow: classified absence, unsafe path or identity,
and integrity mismatch MAY use the established non-disclosing 404. Export
capacity MUST remain 422, transient admission MUST remain 503, and unexpected
I/O such as `ENOMEM` or a programming defect MUST reach the opaque 500 boundary.

#### Scenario: Exact and oversized manifests are distinguished before parse

- **GIVEN** one publication manifest is exactly 16,384 bytes and another is 16,385 bytes
- **WHEN** recovery reads each through its descriptor
- **THEN** the exact manifest may be decoded and parsed
- **AND** the oversized manifest fails before decode or JSON parse with bounded `manifest_bytes` evidence

#### Scenario: Artifact growth is rejected without a second body

- **GIVEN** a regular artifact passes its initial recorded-size check and then grows or truncates during chunked read
- **WHEN** download or recovery verifies its bytes and checksum
- **THEN** verification rejects the inconsistent descriptor evidence
- **AND** it never retains a second whole-file proof Buffer

#### Scenario: Historical oversized artifact is recoverable but not downloadable

- **GIVEN** database authority records a previously committed artifact larger than 67,108,864 bytes
- **WHEN** startup recovery and a later authorized download inspect it
- **THEN** recovery verifies it incrementally without deleting or buffering the whole file
- **AND** download returns 422 `EXPORT_CAPACITY_EXCEEDED` before delivery allocation

#### Scenario: Two maximum downloads fill the pool

- **GIVEN** two active responses each hold a 67,108,864-byte reservation
- **WHEN** another positive-size artifact download requests admission
- **THEN** it receives the existing application-scoped 503 and `Retry-After: 5` before file open
- **AND** either completed or disconnected response releases only its own reservation exactly once

#### Scenario: Unexpected I/O is not hidden as absence

- **GIVEN** artifact lookup succeeded but descriptor reading raises `ENOMEM` or an unclassified I/O failure
- **WHEN** the download route handles the failure
- **THEN** it reaches the opaque 500 boundary
- **AND** it is not reported as 404, 422, or a fabricated terminal Job
