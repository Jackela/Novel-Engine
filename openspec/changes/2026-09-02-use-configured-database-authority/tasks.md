# Tasks

- [x] 1. Add failing API and CLI tests proving a custom `DB_URL` basename is
      preserved across serve, import, backup, doctor, and startup.
- [x] 2. Add failing tests for legacy default-sibling ambiguity before any
      backup, migration, reconciliation, import, or listener side effect.
- [x] 3. Refactor persistence boundaries to accept the exact database path and
      migrate callers without retaining a downstream filename reconstruction.
- [x] 4. Implement and wire the default live SQLite readiness probe with open,
      closed, injected-probe, liveness, and skeleton coverage.
- [ ] 5. Run focused/full validation, browser workflows, strict OpenSpec,
      independent closure review, and record fixed-SHA evidence.
