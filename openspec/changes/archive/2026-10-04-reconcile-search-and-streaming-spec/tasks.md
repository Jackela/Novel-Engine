# Tasks

## T1: Draft the reconciliation deltas

- [x] T1.1 Modify `Full-text search over current content`: cap reduced
      tokens at 3, replace the 30-item cap with bounded pages (default 30,
      maximum 100, honest total, next-offset cursor), and update the
      result-count scenario. Acceptance: delta text matches
      `fts_match_query.ts`, `document_service.ts`, `studio_schemas.ts`, and
      the wave-11 tests (`fts_match_query`, `studio_search_bounds`,
      `studio_search_pagination`).
- [x] T1.2 Modify `Bounded provider response lifecycle`: the deadline covers
      dispatch through the first delivered event, every delivered event
      re-arms it, and silence budgets remain additional ceilings; replace
      the reset assertion with healthy-stream and over-silence scenarios.
      Acceptance: delta text matches `provider_response_lifecycle.ts`
      (`rearm`) and the named cases in `provider_streaming_timeouts.test.ts`.

## T2: Validate

- [x] T2.1 `pnpm spec:validate` passes with the change present.

## T3: Archive

- [x] T3.1 Archive the change; deltas merge into the main spec and the
      change folder moves to `openspec/changes/archive/`.
