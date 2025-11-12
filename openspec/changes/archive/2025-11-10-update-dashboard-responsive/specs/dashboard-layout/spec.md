## ADDED Requirements
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
