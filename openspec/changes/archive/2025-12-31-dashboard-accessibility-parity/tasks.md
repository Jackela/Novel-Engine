## Implementation Tasks
1. Evidence + planning
   - [x] Link MCP audit screenshots/logs to this change and outline acceptance criteria (keyboard activation, API parity, console cleanliness).
   - [x] Align with backend contract for `/characters` payload shape; capture sample fixture for tests.
2. Spec & proposal wiring
   - [x] Update `openspec/specs/dashboard-interactions` with new requirements/scenarios (keyboard semantics, API-backed tiles, quick-action hygiene).
   - [x] Run `openspec validate dashboard-accessibility-parity --strict` once docs/specs are ready.
3. Tests-first (TDD)
   - [x] Add/extend Vitest suites for `WorldStateMapV2`, `CharacterNetworks`, `NarrativeTimeline`, and `QuickActions` to assert keyboard behaviour, aria attributes, and console-silence (use `vi.spyOn(console, 'error')`).
   - [x] Add integration test to confirm map/network consume mocked `/characters` data and reflect counts/names.
4. Implementation
   - [x] Implement roving-tabindex + enter/space handlers and aria metadata for the tiles per spec.
   - [x] Refactor QuickActions to filter props, add focus-visible styles, and broadcast state transitions via accessible text.
   - [x] Introduce data hook/service (e.g., `useCharactersDataset`) reused by map + networks; ensure graceful fallback when API offline.
5. Validation & docs
   - [x] Re-run `npm run lint`, `npm run type-check`, `npm test -- --run` and relevant Playwright accessibility specs.
   - [x] Update audit/UAT docs with new evidence; attach new MCP screenshots if layout changed.
