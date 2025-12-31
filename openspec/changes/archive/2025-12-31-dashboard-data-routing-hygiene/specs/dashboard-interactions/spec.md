## MODIFIED Requirements
### Requirement: Spatial/network tiles consume backend data
World map and character network tiles MUST derive their datasets from the canonical `/api/characters` API (or shared hook), and surface the dataset source state to the UI chips so the feed provenance is explicit.

#### Scenario: Dashboard only hits `/api/characters`
- **GIVEN** MCP console logs from `WorldStateMapV2`/`CharacterNetworks`
- **WHEN** the hook retries after a network failure
- **THEN** every attempted URL includes `/api/characters`
- **AND** the `source` chip shows "API feed" when the endpoint succeeds
- **AND** no request is made to legacy `/characters` paths.

## ADDED Requirements
### Requirement: Router emits no future-flag warnings
The root router MUST opt into `v7_startTransition` and `v7_relativeSplatPath` via `RouterProvider`, and regression tests MUST fail if React Router logs its future-flag warnings.

#### Scenario: App router renders silently
- **GIVEN** the root `<App>` renders inside tests/browsers
- **WHEN** the router initializes
- **THEN** the console contains no "React Router Future Flag Warning" entries and no `ReactDOMTestUtils.act` warnings
- **AND** `src/__tests__/AppRouterWarnings.test.tsx` verifies the router mounts through `createRoot`.
