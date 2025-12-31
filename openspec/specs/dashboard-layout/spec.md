# dashboard-layout Specification

## Purpose
TBD - created by archiving change update-dashboard-responsive. Update Purpose after archive.
## Requirements
### Requirement: Responsive Bento Grid Layout
- **ADDITION**: Control cluster (summary + quick actions) MUST share a single row that does not exceed 180px height on desktop/tablet. `data-role="control-cluster"` wraps both KPI cards and action buttons so automation treats them as one zone.

#### Scenario: Compressed control band
- **GIVEN** the viewport width is ≥ 768px
- **WHEN** the dashboard renders the control band
- **THEN** Summary KPIs and quick-action buttons reside inside one `data-role="control-cluster"` container laid out with `grid-template-columns` (minmax 160px, auto-fit)
- **AND** the band height does not exceed 180px, with buttons right-aligned and no duplicate connection indicator tiles.

### Requirement: Adaptive Header Controls
The dashboard header MUST keep the status info and quick-action buttons accessible on tablets and phones by wrapping/stacking instead of overflowing.

#### Scenario: Tablet header wrap
- **GIVEN** the viewport width is between 768px and 1199px
- **WHEN** the header renders the status pill plus five action buttons
- **THEN** the container allows wrapping so buttons flow onto a second line while preserving 16px min spacing, and no controls overflow the viewport.

#### Scenario: Mobile stacked header
- **GIVEN** the viewport width is ≤ 767px
- **WHEN** the header renders
- **THEN** the status block appears above the actions, the buttons form a two-column grid (or full-width stack) with equal padding, and touch targets remain ≥44px tall.

### Requirement: Flexible Tile Heights
High-variance visualization tiles (world map, narrative timeline, performance metrics) MUST scale their heights responsively to avoid cropped content or extreme whitespace on short viewports.

#### Scenario: Map tile adapts to viewport
- **GIVEN** the world map tile renders on a 360px-tall mobile viewport
- **WHEN** CSS clamps its height with a `min()`/`clamp()` rule
- **THEN** the tile height stays within 45–60% of the viewport height (capping at the desktop max) and maintains full interactivity without overflow scroll bars.

#### Scenario: Metrics/timeline tiles preserve content
- **GIVEN** the timeline and performance metric tiles render on any viewport ≤ 767px
- **WHEN** the layout applies flexible height rules plus internal scroll containers
- **THEN** headings remain visible, progress bars/metrics are not clipped, and the tile content can scroll vertically if it exceeds the clamped height.

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
- **ADDITION**: Desktop first fold MUST include both Streams and Pipeline zones directly beneath the control band, ahead of the Spatial/Backlog zones.

#### Scenario: First fold telemetry density
- **GIVEN** the viewport width is ≥ 1200px
- **WHEN** the dashboard renders the row under the control band
- **THEN** Activity Stream (`data-role="stream-feed"`) and Turn Pipeline (`data-role="pipeline"`) occupy that row, ensuring users see live telemetry without scrolling
- **AND** Spatial tiles (WorldStateMap, CharacterNetworks) share the same fold by capping map height at ≤420px so at least two zones remain visible above the fold.

### Requirement: Flow-based Adaptive Zones
The dashboard MUST organize controls and telemetry into semantic zones rendered via flow layout so panels expand or collapse based on content density rather than fixed tile classes, and the control/pipeline zones stay prominent without duplicating tiles.

#### Scenario: Desktop auto-fit columns
- **GIVEN** the viewport width is ≥ 1200px
- **WHEN** the dashboard renders the Control, Streams, Signals, and Pipeline zones
- **THEN** the layout uses `auto-fit`/`minmax()` columns (≥320px) with `grid-auto-flow: dense` so high-priority zones (Control, Pipeline) may span ≥2 columns while lower-priority zones wrap automatically
- **AND** adjacent zones maintain ≥24px horizontal/vertical gaps regardless of the number of cards inside.

#### Scenario: Tablet stacked flow
- **GIVEN** the viewport width is between 768px and 1199px
- **WHEN** the same zones render
- **THEN** Control + Streams stack as full-width cards, Signals collapses into tabs/accordions, and Pipeline remains visible without horizontal scroll while preserving ≥16px vertical spacing.

#### Scenario: Mobile tabbed flow
- **GIVEN** the viewport width is ≤ 767px
- **WHEN** the dashboard renders
- **THEN** Control, Streams, and Signals zones appear as tabs/accordions in `MobileTabbedDashboard`
- **AND** Control/Pipeline panels can grow vertically without a hard `max-height` clamp while low-priority feeds default to collapsed states.

#### Scenario: Control band pinned above fold
- **WHEN** the viewport width is ≥ 768px
- **THEN** the summary strip and quick-action controls render inside a dedicated control band that spans the full width of the grid (no gaps on desktop/tablet)
- **AND** the band height stays ≤ 240px because quick actions lay out horizontally (two rows max) instead of forming a vertical tower.

#### Scenario: Unique pipeline tile
- **WHEN** the pipeline zone renders
- **THEN** exactly one `<TurnPipelineStatus>` tile is mounted
- **AND** it shares the same auto-fit flow columns as the Streams/System Signals zones so tiles no longer stack twice in the same column.

### Requirement: Semantic Zone Markers
- **ADDITION**: Streams and Pipeline zones MUST expose condensed-mode attributes so tests can distinguish desktop density changes.

#### Scenario: Streams condensed marker
- **GIVEN** the viewport width is ≥ 1200px
- **WHEN** Activity Stream renders the condensed two-column layout
- **THEN** the zone root provides `data-density="condensed"` and each entry exposes deterministic selectors so automation can verify the first fold density target.

