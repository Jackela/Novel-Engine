# Tasks

## 1. Contract-first replacement and budget failures

- [ ] 1.1 Add deterministic story and chapter replacement races proving the
      confined reader never consumes bytes outside its captured workspace and
      rejects an observable source/manuscript/chapters identity change.
- [ ] 1.2 Add exact and plus-one cases for story bytes, chapter bytes, total
      workspace bytes, chapter count, and scanned directory entries. Cover
      multi-byte UTF-8, many small files, and many non-matching entries.
- [ ] 1.3 Add web preview failures proving stable 422/404 classification, zero
      store work, no partial payload, and event-loop responsiveness while a
      large accepted workspace is read.

## 2. Descriptor-owned bounded reader

- [ ] 2.1 Make the reader port asynchronous and introduce one immutable import
      budget policy with the documented fixed defaults.
- [ ] 2.2 Replace `lstat` plus path-based reads with no-follow file handles,
      regular-file and canonical-parent checks, open/path identity comparison,
      bounded chunk reads, and final directory identity validation.
- [ ] 2.3 Replace eager directory loading with bounded asynchronous iteration;
      count every observed entry, cap matching chapters, preserve lexical
      ordering, and close handles/iterators on all failures.
- [ ] 2.4 Preserve the accepted workspace hash and legacy scalar parsing exactly;
      reject instead of truncating, skipping, or silently reweighting content.

## 3. Application, HTTP, and CLI migration

- [ ] 3.1 Await reader completion before any scoped store lookup or write;
      preserve owner/source-hash idempotency and the imported-project transaction.
- [ ] 3.2 Migrate web preview to asynchronous error mapping while preserving
      local-owner, confinement, 404/422/503, response schema, and OpenAPI; expose
      the stable capacity code and bounded resource/limit/observed details.
- [ ] 3.3 Migrate CLI and test doubles to the asynchronous port; preserve accepted
      import ordering, exit codes, database authority, and source read-only
      behavior while replacing full-project output with the bounded
      created/reused import summary.

## 4. Validation and release boundary

- [ ] 4.1 Run focused reader, application, web preview, CLI, idempotency,
      transaction, confinement, and database-authority regressions.
- [ ] 4.2 Run server type-check, lint, architecture, size, full tests, relevant
      event-loop/raw HTTP checks, and strict OpenSpec; record fixed-SHA evidence
      plus every skipped external or human gate.
- [ ] 4.3 Keep the change active until required CI is green, then merge the
      modified requirement into the canonical specification and archive it.
