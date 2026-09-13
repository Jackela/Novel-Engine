# Validation evidence

Delivered via [PR #477](https://github.com/Jackela/Novel-Engine/pull/477) (squash-merged
`95a48d5f`, 2026-09-06). Full record: PR body and
`docs/agents/orchestration-campaign-2026-09-06.md`.

- Inventory of unbounded structure points recorded in design.md; boundaries
  defined with reasoned magnitudes (documents per project, volumes,
  per-volume chapters, beats, settings/metadata byte budgets, title
  lengths).
- Red baseline: the contract suite failed before the domain module existed;
  green on the candidate: 14/14 capacity tests (exact-boundary pass,
  over-limit 422 `STRUCTURE_CAPACITY_EXCEEDED`, no partial writes).
- Layering: limits owned by domain (`structure_capacity.ts`), scalar byte
  assertions in application before store calls, count assertions inside
  the SQLite write transactions (TOCTOU-safe, verified by the
  concurrency/security domain review), eight gated routes mapped to the
  422 envelope; error code registered in the SSOT surfaces.
- Full validation: server 206 files / 1,297 tests (pre-merge head; final
  main 211+/1,32x per campaign closeout), gates clean, frontend generated
  types only, strict OpenSpec 21/21 → 23/23 era.
- Required CI green on the PR head (validate/container/Analyze) after the
  deterministic OpenAPI/api-types regeneration.
- User-facing error text: resource and limit surfaced since #483
  ("… project_volumes limit is 100."), verified in the delegated
  acceptance pass.
