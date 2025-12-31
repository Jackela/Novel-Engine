# dashboard-interactions Specification

## Purpose
TBD - created by archiving change improve-dashboard-map-ui. Update Purpose after archive.
## Requirements
### Requirement: Entity selection reveals context panel
The world map tile MUST expose a visible details panel that updates whenever a character marker is selected so the interaction produces actionable information.

#### Scenario: Details render for the active entity
- **GIVEN** the dashboard renders entity markers on the world map
- **WHEN** the user activates (clicks or keyboard-selects) a marker
- **THEN** a details panel becomes visible without leaving the tile
- **AND** it displays the character's name, role/type, status, and key stats pulled from the same dataset
- **AND** only that entity is marked as selected until another selection occurs.

#### Scenario: Keyboard users can inspect the selection
- **GIVEN** a keyboard-only user tabs to a marker
- **WHEN** they press Enter or Space to activate it
- **THEN** the same details panel content updates and focus/ARIA states reflect the new selection without requiring a mouse.

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

