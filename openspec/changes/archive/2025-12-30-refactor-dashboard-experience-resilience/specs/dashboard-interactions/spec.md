## ADDED Requirements
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
