# dashboard-interactions Specification

## Purpose
TBD - created by archiving change improve-dashboard-map-ui. Update Purpose after archive.
## Requirements
### Requirement: Entity selection reveals context panel
The world map tile MUST expose a visible details panel that updates whenever a character marker is selected so the interaction produces actionable information, and markers MUST be keyboard operable with deterministic aria attributes that convey selection and panel linkage.

#### Scenario: Details render for the active entity
- **GIVEN** the dashboard renders entity markers on the world map
- **WHEN** the user activates (clicks or keyboard-selects) a marker
- **THEN** a details panel becomes visible without leaving the tile
- **AND** it displays the character's name, role/type, status, and key stats pulled from the same dataset
- **AND** only that entity is marked as selected until another selection occurs.

#### Scenario: Keyboard users can inspect the selection
- **GIVEN** a keyboard-only user tabs to a marker
- **WHEN** they press Enter or Space to activate it
- **THEN** the marker exposes `role="button"`, `tabindex="0"`, `aria-selected="true"`, and `aria-controls` referencing the details region
- **AND** the same details panel content updates and focus/ARIA states reflect the new selection without requiring a mouse.

### Requirement: Live telemetry indicator refreshes on a timer
The "Live" header badge MUST pair with a timestamp that refreshes on an interval ≤30s even if no other state changes, and announce updates politely for assistive tech.

#### Scenario: Timestamp updates idly
- **GIVEN** the dashboard remains idle for 60 seconds
- **WHEN** 30 seconds elapse
- **THEN** the timestamp text updates to the current time without a manual refresh
- **AND** the container exposes `aria-live="polite"` so screen readers announce the change without stealing focus.

### Requirement: Single quick-action cluster with run-state summary
Quick-action controls MUST appear once in the dashboard header and be accompanied by a run-state summary tile that mirrors the current pipeline state without duplicating the buttons.

#### Scenario: Run-state tile mirrors controls
- **GIVEN** the header renders Start/Pause/Stop/Refresh buttons
- **WHEN** the dashboard also renders the run-state tile
- **THEN** that tile shows the current pipeline state (e.g., Running, Paused) plus timestamp/phase info but does not introduce duplicate actionable buttons, so keyboard focus order stays concise.

### Requirement: Connection indicator reflects offline recovery
The dashboard connection indicator MUST expose deterministic states (LIVE/ONLINE/STANDBY/OFFLINE) with `data-status` attributes so automated tests can assert behaviour during network interruptions and recovery.

#### Scenario: Offline transition and recovery
- **GIVEN** the dashboard renders the connection indicator (`data-testid="connection-status"`/`data-testid="live-indicator"`)
- **WHEN** network access drops (simulated via `page.context().setOffline(true)`)
- **THEN** the indicator switches to `data-status="offline"`, shows the OFFLINE label, and announces the change via `aria-live="polite"`
- **AND** once connectivity returns the indicator flips back to ONLINE/LIVE and the guest/summary strip timestamps resume updating.

### Requirement: Core panels render with fallback data in offline/guest contexts
The dashboard MUST render the world map, pipeline status, and system log tiles with deterministic mock/guest data when API calls fail, so users and tests can still observe state and accessibility cues.

#### Scenario: Panels render under mock data after offline navigation
- **GIVEN** a user navigates to `/dashboard` with guest mode enabled and the network offline
- **WHEN** the dashboard loads
- **THEN** the world map tile (`data-testid="world-state-map"`), pipeline tile (`data-testid="turn-pipeline-status"`), and system log (`data-testid="system-log"`) render visible content sourced from fallback data
- **AND** the connection indicator remains present with `data-status="offline"` until connectivity returns.

### Requirement: Skeletons dismiss within a bounded time window
Dashboard skeleton/loading states MUST dismiss or be replaced by fallback content within 5 seconds of navigation so keyboard and screen-reader users can reach interactive panels even when live data is unavailable.

#### Scenario: Skeleton auto-dismisses to accessible panels
- **WHEN** a user lands on `/dashboard` without live API data
- **THEN** any skeleton container (e.g., `data-testid="skeleton-dashboard"`) is removed or hidden within 5 seconds
- **AND** focusable controls inside the dashboard (tabs, quick actions, map markers) become reachable with correct `aria`/`data-testid` attributes.

### Requirement: Character network exposes actionable nodes
Character network cards MUST be reachable via keyboard focus, announce status/trust, and support Enter/Space to open their mini detail row.

#### Scenario: Character cards are operable without a mouse
- **GIVEN** the user tabs through `[data-role="character-networks"]`
- **WHEN** focus lands on a character card
- **THEN** the card element has `role="button"`, `tabindex="0"`, and `aria-pressed`/`aria-expanded` to indicate activation
- **AND** pressing Enter/Space triggers the same handler as clicking.

### Requirement: Timeline nodes are keyboard navigable
Each narrative timeline node MUST participate in a roving tablist so users can inspect current, completed, and upcoming entries with consistent aria metadata.

#### Scenario: Timeline exposes aria-current status
- **GIVEN** focus is inside `[data-role="narrative-timeline"]`
- **WHEN** the user arrows or tabs through timeline nodes
- **THEN** only the active node has `tabindex="0"` (`-1` for others)
- **AND** the current node exposes `aria-current="step"` and Enter/Space triggers the same callbacks used for pointer events.

### Requirement: QuickActions controls are accessible without invalid DOM props
QuickActions controls MUST be keyboard accessible, retain visible focus outlines, and avoid leaking custom props to the DOM.

#### Scenario: QuickActions render without DOM warnings
- **GIVEN** QuickActions render in any state (idle or running)
- **WHEN** React strict-mode checks props
- **THEN** no custom props (e.g., `active`) reach the DOM
- **AND** focus outlines remain visible for keyboard navigation.

### Requirement: Spatial/network tiles consume backend data
World map and character network tiles MUST derive their datasets from the canonical `/api/characters` API (or shared hook), and surface the dataset source state to the UI chips so the feed provenance is explicit.

#### Scenario: Dashboard only hits `/api/characters`
- **GIVEN** MCP console logs from `WorldStateMapV2`/`CharacterNetworks`
- **WHEN** the hook retries after a network failure
- **THEN** every attempted URL includes `/api/characters`
- **AND** the `source` chip shows "API feed" when the endpoint succeeds
- **AND** no request is made to legacy `/characters` paths.

### Requirement: Router emits no future-flag warnings
The root router MUST opt into `v7_startTransition` and `v7_relativeSplatPath` via `RouterProvider`, and regression tests MUST fail if React Router logs its future-flag warnings.

#### Scenario: App router renders silently
- **GIVEN** the root `<App>` renders inside tests/browsers
- **WHEN** the router initializes
- **THEN** the console contains no "React Router Future Flag Warning" entries and no `ReactDOMTestUtils.act` warnings
- **AND** `src/__tests__/AppRouterWarnings.test.tsx` verifies the router mounts through `createRoot`.

