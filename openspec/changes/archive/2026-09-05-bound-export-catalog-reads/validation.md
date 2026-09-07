# Validation evidence

Delivered via [PR #474](https://github.com/Jackela/Novel-Engine/pull/474) (squash-merged
`a253723b`, 2026-09-06). Measurement, design, and implementation were
authored under the orchestration campaign; the record lives in the PR body
and `docs/agents/orchestration-campaign-2026-09-06.md`.

- Measured quadratic paths: session-catalog traffic `E(E+1)/2` artifacts →
  `E×50` bounded pages (200 exports: 18.5 MB per response → one page max);
  snapshot assembly `14+N` statements (200 docs = 214) → constant **15
  statements / 1 batched INSERT** (flat across 25/50/100/200).
- Contract-first red (tasks 1.1–1.4 recorded in the first session) → green
  on the merged candidate: server 204 files / 1,284 tests, gates clean,
  frontend 89 files / 485 tests, type/lint/format/build/drift clean, strict
  OpenSpec passing.
- Migration `0021_paginate-export-catalog` regenerated off the merged base
  after the parallel-branch renumber (journal chain 0020→0021 verified;
  index-only, no data change).
- Required CI green on the PR head (validate/container/Analyze).
- Browser coverage: export failure/retry, Load-older traversal, and
  terminal focus exercised by the #476 workflows and the delegated
  acceptance packet (12/12, 2026-09-06).
