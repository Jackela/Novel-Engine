# Validation evidence

Delivered via [PR #475](https://github.com/Jackela/Novel-Engine/pull/475) (squash-merged
`81eed2cb`, 2026-09-06). Full record: PR body and
`docs/agents/orchestration-campaign-2026-09-06.md`.

- N+1 measurement: `2 + 3N` statements before (1/5/10/20 reviews →
  5/17/32/62), 557,120 bytes of snapshot bodies per 20-review list; after:
  **fixed 3 statements per page, 4 per detail**, zero body columns, EXPLAIN
  QUERY PLAN index-backed via `idx_reviews_project_created_id`
  (migration `0022`).
- Contract-first red → green with full revalidation after the rebase
  resolution: server 209 files / 1,307 tests, gates clean, frontend 92
  files / 507 tests, strict OpenSpec 22/22 (pre-merge head) — superseded by
  final main runs recorded in the campaign closeout.
- react-doctor zero-diagnostic pass included (ref-in-effect + paging prop
  shape repairs during integration).
- Required CI green on the PR head after rebase (validate/container/
  Analyze), plus one infra-flake rerun recorded honestly.
- Browser coverage: review run workflow, request isolation, and failure
  matrix via the #476 workflows; delegated acceptance packet 12/12.
