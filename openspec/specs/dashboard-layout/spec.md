# dashboard-layout Specification

## Purpose
TBD - created by archiving change update-dashboard-responsive. Update Purpose after archive.
## Requirements
### Requirement: Responsive Bento Grid Layout
The dashboard grid MUST use class-based column spans so “large”, “medium”, and “small” tiles render the intended arrangement across desktop, tablet, and mobile breakpoints without inline overrides.

#### Scenario: Desktop 12-column layout
- **GIVEN** the viewport width is ≥ 1200px
- **WHEN** the dashboard renders the `.tile-large`, `.tile-medium`, and `.tile-small` elements
- **THEN** `.tile-large` spans 6 of 12 columns, `.tile-medium` spans 4 of 12, and `.tile-small` spans 3 of 12 (wrapping as needed)
- **AND** the grid uses the shared spacing/padding defined in the design system or `<BentoGrid>` component.

#### Scenario: Tablet 8-column layout
- **GIVEN** the viewport width is between 768px and 1199px
- **WHEN** the dashboard renders the same tiles
- **THEN** large and medium tiles expand to span the full 8-column width, while small tiles span 4 columns so two fit per row
- **AND** no horizontal scrolling is required to view any tile.

#### Scenario: Mobile single-column layout
- **GIVEN** the viewport width is ≤ 767px
- **WHEN** the dashboard renders
- **THEN** every tile spans the single available column with consistent vertical spacing and padding
- **AND** content within each tile remains fully visible without horizontal scrolling.

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

### Requirement: Flow-based Adaptive Zones
The dashboard MUST organize controls and telemetry into semantic zones rendered via flow layout so panels expand or collapse based on content density rather than fixed tile classes.

#### Scenario: Desktop auto-fit columns
- **GIVEN** the viewport width is ≥ 1200px
- **WHEN** the dashboard renders the Control, Streams, Signals, and Pipeline zones
- **THEN** the layout uses `auto-fit`/`minmax()` columns (≥260px) with `grid-auto-flow: dense` so high-priority zones (Control, Pipeline) may span ≥2 columns while lower-priority zones wrap automatically
- **AND** adjacent zones maintain ≥24px horizontal/vertical gaps regardless of the number of cards inside.

#### Scenario: Tablet stacked flow
- **GIVEN** the viewport width is between 768px and 1199px
- **WHEN** the same zones render
- **THEN** Control + Streams stack as full-width cards, Signals collapses into tabs/accordions, and Pipeline remains visible without horizontal scroll while preserving ≥16px vertical spacing.

#### Scenario: Mobile tabbed flow
- **GIVEN** the viewport width is ≤ 767px
- **WHEN** the dashboard renders
- **THEN** Control, Streams, and Signals zones appear as tabs/accordions in `MobileTabbedDashboard`, ensuring only one high-density panel is expanded at a time and each control keeps ≥44px touch targets.

### Requirement: Semantic Zone Markers
Each zone MUST expose semantic identifiers so automation/AI routines and tests can target them without relying on visual ordering.

#### Scenario: Data-role attributes
- **GIVEN** the dashboard renders
- **WHEN** inspecting the DOM
- **THEN** each zone container provides a stable `data-role` (e.g., `data-role="control-cluster"`, `data-role="stream-feed"`, `data-role="system-signals"`, `data-role="pipeline"`)
- **AND** critical child controls (quick actions, pipeline steps) retain deterministic `data-testid`s nested within those zones.

#### Scenario: Overflow-friendly feeds
- **GIVEN** the Streams or Signals zone receives more than 6 activity/event items
- **WHEN** the zone renders
- **THEN** it caps visual height via internal scroll or virtualization so the overall layout does not push lower zones off-screen, while the zone’s `data-role` container remains intact for interaction hooks.

