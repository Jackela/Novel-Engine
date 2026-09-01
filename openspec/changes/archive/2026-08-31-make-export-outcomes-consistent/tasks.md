# Tasks

- [x] 1. Capture fixed-SHA baseline failures for orphan export snapshots and
      artifact/job split publication.
- [x] 2. Replace snapshot-first export persistence with a typed read-only source
      and atomic outcome port.
- [x] 3. Land fresh and retry snapshot/artifact/job evidence in immediate
      transactions with source revalidation and failure-injection seams.
- [x] 4. Compensate published files without masking database failures and wire
      cleanup reporting through fresh and retry routes.
- [x] 5. Generate and test the historical orphan-export-snapshot cleanup
      migration.
- [x] 6. Replace unordered revision-map reuse with direct equality over the
      complete ordered source projection and prove reorder invalidation.
- [x] 7. Add durable stage/manifest publication, a write-ahead cleanup-intent
      journal, identity-safe quarantine rollback, and pre-serve crash
      reconciliation.
- [x] 8. Move project artifact cleanup out of the database store, add safe
      confinement, and enforce project-exclusive deletion semantics.
- [x] 9. Record the cross-authority decision and reconcile the canonical
      OpenSpec requirements with restart and cleanup behavior.
- [x] 10. Run focused and full validation on an exact candidate SHA, obtain
      independent red-team reviews, and record skipped external gates.
