## MODIFIED Requirements
### Requirement: Spatial/network tiles consume backend data
- **ADDITION**: `useDashboardCharactersDataset` MUST exclusively target the canonical `/api/characters` feed and surface its source state to the UI chips.

#### Scenario: Dashboard only hits `/api/characters`
- **GIVEN** MCP console logs from `WorldStateMapV2`/`CharacterNetworks`
- **WHEN** the hook retries after a network failure
- **THEN** every attempted URL includes `/api/characters`, the `source` chip shows “API feed” when the endpoint succeeds, and no request is made to legacy `/characters` paths.

### Requirement: Router emits no future-flag warnings
- **ADDITION**: The root router MUST opt into `v7_startTransition` & `v7_relativeSplatPath` via `RouterProvider`, and regression tests should fail if React Router logs its future-flag warnings.

#### Scenario: App router renders silently
- **GIVEN** the root `<App>` renders inside tests/Browsers
- **WHEN** the router initializes
- **THEN** the console contains no “React Router Future Flag Warning” entries and no `ReactDOMTestUtils.act` warnings, as verified by `src/__tests__/AppRouterWarnings.test.tsx` mounting through `createRoot`.
