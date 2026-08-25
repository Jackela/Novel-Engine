# Rewrite slice 2 — authoring core and data model

## Why

Slice 1 gave the `novel-engine` capability its contract foundation. This
second slice backfills the authoring core the pre-rewrite audit found living
only in code: the data-model adjudication (#247, C1–C10), the save and
ordering semantics (#248, D7/D8), and the FTS5 full-text search behavior the
audit ranked the largest specification gap (B1). Without these Requirements
the rewrite could silently drop immutable revisioning, safe search, the
uniqueness family, and the self-hosted durability posture.

## What Changes

- Adds authoring-core Requirements to the `novel-engine` capability: SQLite
  authority with immutable, atomically advanced revisions; save semantics
  (same-request title/metadata, monotonic numbering with a parent chain, the
  server-assigned closed source enum); FTS5 search with strict token
  reduction and transactional index sync; the uniqueness family — (project,
  kind, title), per-document revision numbers, and snapshot-document pairs;
  stable list ordering and full-set reorder renumbering; durable single-file
  operation (startup backup, restart integrity, cascades); restart job
  recovery with the explicit no-invented-lease clause (C8); and startup
  schema migration with the backup-first ordering (C9).
- These Requirements compose with slice 1's contract foundation: stale saves
  reuse the Unified error envelope's `REVISION_CONFLICT` shape and partial
  reorders reuse the Request validation constraints — referenced, not
  redefined.
- Snapshot-bound review and export behavior (D2–D6), proposal jobs, provider
  contracts, and import land in slice 3, per the #252 slice map.

## Impact

- The `novel-engine` capability gains its second Requirement block;
  `novel-studio` stays valid until the cutover change retires it.
- The search endpoint, save conflict payload, and reorder behavior are
  already frontend-consumed; this slice introduces no frontend contract
  change.
- This slice feeds the #252 mandatory e2e list: FTS5 search correctness with
  operator-laden input, and the 409 conflict payload shape with
  `details.current_revision_id`.
