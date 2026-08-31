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
- [ ] 6. Run focused and full validation on an exact candidate SHA, obtain
      independent red-team reviews, and record skipped external gates.
