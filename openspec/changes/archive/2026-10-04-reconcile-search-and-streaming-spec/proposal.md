# Reconcile the search and streaming requirements with shipped behavior

## Why

The 2026-10-01 devil's-advocate fix campaign changed three observable
behaviors and updated the spec in most places, but three sentences in
`openspec/specs/novel-engine/spec.md` still describe the pre-campaign
contract:

- The search requirement still caps the reduced query at 8 tokens; the
  shipped cap is 3 (DR-030, wave 11: eight-element adversarial queries
  measured 453–970 ms of event-loop freeze over the 6.16 MiB corpus, while
  three elements measured ~71 ms).
- It still states results MUST NOT exceed 30 items; shipped search returns
  bounded, walkable pages — default page size 30, hard maximum 100, an
  honest total, and a next-offset cursor (DR-029, wave 11).
- The provider lifecycle requirement still says the absolute deadline MUST
  NOT reset after any frame; shipped streaming re-arms the deadline on every
  delivered event so healthy long streams survive, while the silence budgets
  still abort stalls (DR-026, wave 10c2).

Shipped, tested behavior therefore contradicts the SSOT. This change
reconciles the requirement text and scenarios; it changes no behavior.

## What Changes

- `Full-text search over current content`: the reduced-token cap goes 8 → 3;
  the 30-item cap becomes bounded, walkable pages (default 30, maximum 100,
  honest total, next-offset cursor); the "Result count is bounded" scenario
  becomes "Result pages are bounded and walkable".
- `Bounded provider response lifecycle`: the absolute deadline covers
  dispatch through the first delivered event and every delivered event
  re-arms it; the first-event and between-event silence budgets remain
  additional ceilings; the "deadline has not reset after any response byte
  or frame" assertion is replaced by scenarios for a healthy re-arming
  stream and for an over-silent stream that still aborts.
- No other requirement text changes.

## Impact

- Spec-only: no code, no schema, no API shape, no migration, no dependency,
  no configuration. The described behavior already shipped in commits
  `2c8393b0` (DR-026 deadline re-arm) and `636fc7b5` (DR-029 pagination,
  DR-030 token cap) on `fix/devil-advocate-backlog`, with the campaign's
  full gates recorded in
  `docs/audits/2026-10-01-devil-advocate-fix-backlog.md`.
- Retroactive reconciliation: the campaign edited the spec directly per
  wave; this change backfills the formal delta for the three untouched
  sentences. Tasks are drafting, validation, and archiving only.
