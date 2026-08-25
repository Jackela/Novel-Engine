## 1. Specification

- [x] 1.1 Draft the authoring-core and data-model deltas in the `novel-engine` capability
- [x] 1.2 `pnpm spec:validate` green

## 2. Server implementation (per `/to-tickets` breakdown)

- [x] 2.1 Conflict-checked save with atomic revision creation/advance and the server-assigned source enum
- [x] 2.2 Uniqueness family enforcement: (project, kind, title), per-document revision numbers, snapshot-document pairs
- [x] 2.3 FTS5 search module: token reduction, parameterized match, ranked plain-text snippets, transactional index sync
- [x] 2.4 Ordering: projects `updated_at` DESC, documents (kind, position, created_at), full-set reorder renumbering 1..n
- [x] 2.5 Startup sequence: online backup, programmatic migrations, running-job → interrupted with event
- [x] 2.6 Durability posture: crash-safe single-file database with enforced referential integrity and cascade deletes

## 3. Verification

- [x] 3.1 Contract tests: save conflict shape, monotonic revision chain, duplicate identity rejection, ordering, reorder renumbering
- [x] 3.2 Search tests: ranked snippets, operator-laden input reduction, tokenless queries, stale-index absence, 30-result bound
- [x] 3.3 Restart/durability tests: abrupt-stop integrity, backup-before-migration ordering, interrupted-job recovery, upgrade first boot
- [x] 3.4 e2e feed for the #252 mandatory list: search correctness and the 409 conflict payload
