## Implementation Tasks
1. Audit and classify routes
   - [ ] Inventory all FastAPI route prefixes and list “product API” vs “tooling/observability API”.
   - [ ] Find and document all `/api/v1` references in code/docs; label each as “must keep”, “must migrate”, or “remove”.

2. Standardize the product API policy
   - [ ] Ensure product endpoints exist under `/api/*` (canonical).
   - [ ] Ensure a `/api/v1/*` alias exists for v1 product endpoints (same behavior).
   - [ ] Ensure any route discovery/endpoints map only lists real routes (no stale `/api/v1/characters` references if not served).

3. Update docs and examples
   - [ ] Update docs under `docs/api/` and examples under `examples/` to match the policy (frontend uses `/api`, external examples may use `/api/v1`).
   - [ ] Update security config allowlists/deny rules referencing old paths.

4. Tests and validation
   - [ ] Add/extend contract tests ensuring `/api/*` and `/api/v1/*` return equivalent responses for the product surface.
   - [ ] Run full CI validation suite and `openspec validate standardize-api-surface --strict`.

