# Tasks

- [x] 1. Add a typed proposal-acceptance persistence port and Drizzle adapter.
- [x] 2. Add failure-injection tests proving revision, pointer, FTS, project,
      and job binding roll back as one unit.
- [x] 3. Add independent-store idempotence and legacy split-repair tests.
- [x] 4. Route `AiProposalService.adoptProposal` through the atomic command and
      remove its obsolete document-service dependency.
- [x] 5. Run focused tests and all applicable server/OpenSpec validation, then
      record exact candidate evidence and independent review status.
