## Implementation Tasks
1. Evidence + planning
   - [ ] Link MCP audit screenshots/logs to this change and outline acceptance criteria (keyboard activation, API parity, console cleanliness).
   - [ ] Align with backend contract for `/characters` payload shape; capture sample fixture for tests.
2. Spec & proposal wiring
   - [ ] Update `openspec/specs/dashboard-interactions` with new requirements/scenarios (keyboard semantics, API-backed tiles, quick-action hygiene).
   - [ ] Run `openspec validate dashboard-accessibility-parity --strict` once docs/specs are ready.
3. Tests-first (TDD)
   - [ ] Add/extend Vitest suites for `WorldStateMapV2`, `CharacterNetworks`, `NarrativeTimeline`, and `QuickActions` to assert keyboard behaviour, aria attributes, and console-silence (use `vi.spyOn(console, 'error')`).
   - [ ] Add integration test to confirm map/network consume mocked `/characters` data and reflect counts/names.
4. Implementation
   - [ ] Implement roving-tabindex + enter/space handlers and aria metadata for the tiles per spec.
   - [ ] Refactor QuickActions to filter props, add focus-visible styles, and broadcast state transitions via accessible text.
   - [ ] Introduce data hook/service (e.g., `useCharactersDataset`) reused by map + networks; ensure graceful fallback when API offline.
5. Validation & docs
   - [ ] Re-run `npm run lint`, `npm run type-check`, `npm test -- --run` and relevant Playwright accessibility specs.
   - [ ] Update audit/UAT docs with new evidence; attach new MCP screenshots if layout changed.
