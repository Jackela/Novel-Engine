# Tasks

## 1. Contract-first high-cardinality coverage

- [x] 1.1 Add a failing production-store regression with complete captured
      sources at 32,765, 32,766, and 32,767 revisions; prove valid exports do
      not raise SQLite parameter exhaustion and preserve every ordered source
      entry.
- [x] 1.2 Add failing empty and duplicate collection cases. Preserve the
      existing no-chapter 422 with zero file/database evidence for empty input,
      and require duplicate document or revision identities to remain visible
      invariant defects rather than silent deduplication or fabricated failed
      Jobs.
- [x] 1.3 Delete or wrongly scope a captured revision in a later query group and
      prove the complete source is invalidated; separately mutate persisted
      immutable content/metadata and prove the defect remains opaque. No prefix
      may be accepted and no snapshot, artifact, completed Job, or event commits.

## 2. Bounded exact revalidation

- [x] 2.1 Extract or adapt one narrow production revision-query helper with an
      explicit parameter budget that includes every non-collection binding;
      keep query construction parameterized.
- [x] 2.2 Execute every bounded group through the same existing immediate
      export-landing transaction, accumulate compound document/revision
      identities, and compare the complete cardinality, content, and metadata
      only after all groups return.
- [x] 2.3 Validate duplicate and conflicting captured identities before query
      execution; handle the empty collection without emitting invalid SQL or
      changing the established no-chapter response.

## 3. Atomic failure and compensation regressions

- [x] 3.1 Re-run fresh and retry source-invalidation tests and prove their
      current public outcomes remain stable at a group boundary.
- [x] 3.2 Inject failure after complete revalidation and at snapshot, artifact,
      Job, and event writes; prove one immediate transaction leaves zero partial
      database evidence.
- [x] 3.3 Exercise the real filesystem publication seam and prove a post-render
      revalidation/landing failure performs identity-aware file compensation;
      cleanup-reporting failure must not mask the original error.

## 4. Validation and release boundary

- [x] 4.1 Run focused export store, outcome, retry, artifact publication,
      cleanup-journal, and startup-recovery regressions, including the actual
      production query path at all three cardinality boundaries.
- [x] 4.2 Run server type-check, lint, architecture, size, migration-channel,
      full test, and strict OpenSpec gates; record exact commands, results,
      fixed SHA, and skipped external gates.
- [ ] 4.3 Keep the change active until required CI is green, then merge the
      complete modified requirement into the canonical specification before
      archiving the unchanged change folder.
