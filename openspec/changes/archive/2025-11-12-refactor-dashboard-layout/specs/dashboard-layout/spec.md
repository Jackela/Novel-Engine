## ADDED Requirements
### Requirement: Summary Strip and Quick Actions Tile
The dashboard MUST present a first-row summary strip plus a dedicated `quick-actions` tile so primary KPIs and orchestration controls are discoverable and testable.

#### Scenario: Summary strip highlights KPIs
- **GIVEN** the dashboard loads on desktop
- **WHEN** data for health, active turn, queue depth, and last refresh is available
- **THEN** a summary strip displays those KPIs with concise labels and status pills above the main grid
- **AND** the strip updates in sync with query results (showing placeholders while loading).

#### Scenario: Quick-actions tile exposes controls
- **GIVEN** the dashboard renders on any breakpoint
- **WHEN** the quick actions tile mounts
- **THEN** it renders within a container that sets `data-testid="quick-actions"` and includes buttons with deterministic `data-testid` values (`quick-action-play`, `quick-action-pause`, `quick-action-stop`, `quick-action-refresh`)
- **AND** those controls emit state updates consumed by pipeline/activity tiles.

#### Scenario: Mobile-friendly quick actions
- **GIVEN** the viewport width is ≤ 767px
- **WHEN** the quick actions tile renders
- **THEN** the buttons arrange in a horizontal scroll list or stacked rows with ≥44px touch targets, without overflowing the viewport.

### Requirement: Zone-based Responsive Layout
The dashboard MUST group tiles into clearly defined zones (Summary, Spatial, Streams, Backlog) with breakpoint-specific ordering so high-priority information stays above the fold.

#### Scenario: Desktop zones
- **GIVEN** the viewport width is ≥ 1200px
- **WHEN** the layout engine computes grid placements
- **THEN** the summary strip spans the full width, the Spatial zone (map, networks, timeline) occupies the primary columns, Streams (activity, pipeline, metrics) align adjacent, and Backlog tiles (recent projects, characters) stay in the rightmost/lowest zone.

#### Scenario: Tablet reflow
- **GIVEN** the viewport width is between 768px and 1199px
- **WHEN** the layout renders
- **THEN** Summary + Quick Actions stay on the first row, Spatial and Streams stack into two columns with balanced heights, and Backlog collapses into accordions below them.

#### Scenario: Mobile condensed view
- **GIVEN** the viewport width is ≤ 767px
- **WHEN** the layout renders
- **THEN** Summary cards and Quick Actions appear first, Spatial/Streams content is accessible via tabs or accordions (one active view at a time), and backlog sections are collapsed by default to limit scroll length.
