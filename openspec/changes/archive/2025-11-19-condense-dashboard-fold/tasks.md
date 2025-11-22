## Implementation Tasks
1. Planning & scaffolding
   - [x] Validate current MCP evidence and confirm opportunity areas (control band height, missing streams in first fold).
   - [x] Update design notes (or reuse existing) with target grid structure and spacing tokens.
2. Layout restructuring
   - [x] Refactor `Dashboard.tsx` so `SummaryStrip` + `QuickActions` render inside a shared `ControlCluster` component spanning 100% width on desktop/tablet, ≤180px tall.
   - [x] Reorder zone rendering so Activity Stream + Turn Pipeline occupy the first row beneath the control band while WorldStateMap shares the row with CharacterNetworks.
   - [x] Update `BentoGrid` / styles to support the new flow ordering and height clamps.
3. Component polish
   - [x] Simplify `QuickActions` visual treatment (no duplicate standby pills, align buttons) and ensure `data-testid` hooks persist.
   - [x] Add condensed layout props to `RealTimeActivity` (two-column desktop table) and cap `WorldStateMapV2` height to ~420px on desktop.
4. Tooling & docs
   - [x] Adjust Playwright POM/selectors if zone positions change; rerun core/extended/accessibility suites.
   - [x] Capture new MCP screenshot + metadata, update README/docs references.
5. Validation
   - [x] Rerun `npm run lint`, `npm run type-check`, `npm test -- --run`.
   - [x] Rerun required Playwright specs.
   - [x] Document results in `docs/testing/uat` and ensure OpenSpec change validates (`openspec validate condense-dashboard-fold --strict`).
