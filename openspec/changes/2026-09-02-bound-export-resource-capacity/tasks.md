# Tasks

## 1. Boundary-first domain and source capture

- [ ] 1.1 Add exact and plus-one production-store tests for 65,536 source
      documents and 16,777,216 raw UTF-8 source bytes, covering project title,
      all six variable document fields, multi-byte text, non-chapters, and
      bounded `observed` values.
- [ ] 1.2 Add one immutable export-capacity policy and typed
      `ExportCapacityExceededError` with closed resource names and safe integer
      validation; add the stable error code/message/details to the HTTP and
      agent error catalogs.
- [ ] 1.3 Measure document count and byte totals in the same persistence read
      transaction before source rows materialize, then preserve complete
      ordering, snapshot reuse, and the existing grouped source revalidation.

## 2. Renderer and publication limits

- [ ] 2.1 Add exact 67,108,864-byte and plus-one renderer tests for Markdown,
      DOCX, and EPUB using bounded sinks/test seams, proving no truncation or
      stage/manifest/final/database evidence on refusal.
- [ ] 2.2 Add one app-local, opaque-token renderer permit with limit one;
      acquire it before source capture and keyed-retry reservation, hold it
      through landing/acknowledgement/rollback and Buffer release, and prove
      generation-safe exact-once release on every exit.
- [ ] 2.3 Replace unbounded joined/ZIP/document output accumulation with bounded
      serialization that stops at the first byte above the artifact limit while
      preserving byte-exact accepted Markdown, DOCX, and EPUB contracts.
- [ ] 2.4 Enforce descriptor size and artifact limit before publication, retain
      identity-aware compensation, and prove all database/file evidence remains
      all-or-nothing after boundary and injected landing failures.

## 3. Bounded artifact proof and recovery

- [ ] 3.1 Add descriptor race tests for exact/plus-one and sparse artifacts,
      growth, truncation, final-path replacement, short reads, and checksum
      mismatch; assert allocation never precedes regular-file and size checks.
- [ ] 3.2 Implement one no-follow descriptor-owned read/hash primitive using a
      maximum 65,536-byte chunk, exact-size delivery allocation, incremental
      SHA-256, and post-read growth/truncation/identity rejection.
- [ ] 3.3 Migrate rollback, acknowledgement, and recovery proofs to retain only
      identity/size/checksum, hash files sequentially, and avoid simultaneous
      stage/final/quarantine bodies.
- [ ] 3.4 Add exact 16,384-byte and plus-one manifest tests before decode/parse;
      prove oversized uncommitted evidence fails closed without unauthorized
      deletion and oversized committed legacy artifacts recover incrementally
      but remain undownloadable.

## 4. HTTP, retry, and download ownership

- [ ] 4.1 Add fresh export tests for each permanent resource failure returning
      422 `EXPORT_CAPACITY_EXCEEDED` with bounded details and no Job, snapshot,
      artifact, file, manifest, cleanup intent, or event.
- [ ] 4.2 Add keyed export-retry tests proving one failed Job/event and identical
      422 replay for the same key, no repeated rendering/evidence, a new attempt
      for a different key, and no retry reservation on renderer 503 refusal.
- [ ] 4.3 Add an app-local 134,217,728-byte download reservation guard; reserve
      recorded bytes before file open, hold through response finish/close, and
      prove two exact 64 MiB responses fill the pool, the next positive request
      receives 503, and success/error/disconnect release exactly once.
- [ ] 4.4 Narrow artifact error catches and test classified 404, permanent 422,
      transient 503, unexpected I/O 500, and programming-defect 500 without
      leaking paths or changing known publication-write auditing.
- [ ] 4.5 Declare the new envelopes on fresh export, retry, and download routes;
      preserve existing transient capacity schema and `Retry-After`, regenerate
      OpenAPI and frontend API types, and pass drift/CORS checks.

## 5. Integrated boundaries and release evidence

- [ ] 5.1 Run the 32,765/32,766/32,767 source-identity regressions together with
      source byte/count bounds to prove the earlier SQLite fix remains intact.
- [ ] 5.2 Run fresh/retry/download API tests, render-format fixtures, publication
      crash/rollback/recovery tests, server type-check/lint/arch/size/full tests,
      API-types drift, frontend type-check, and strict OpenSpec.
- [ ] 5.3 Record fixed-baseline evidence and explicit skips; keep catalog and
      recovery enumeration pagination plus immediate per-group source-result
      disposal as named later changes, not hidden completion claims.
- [ ] 5.4 Keep the change active until required CI is green, then merge its
      requirements into the canonical specification and archive it.
