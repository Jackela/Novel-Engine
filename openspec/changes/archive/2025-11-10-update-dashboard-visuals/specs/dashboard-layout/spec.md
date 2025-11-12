## MODIFIED Requirements
### Requirement: Responsive Bento Grid Layout
The dashboard grid MUST use class-based column spans so tiles render consistently across desktop, tablet, and mobile breakpoints.

#### Scenario: Extra-wide desktops (≥1440px)
- **WHEN** the viewport width is ≥ 1440px
- **THEN** `.tile-xl` spans 8 of 16 columns, `.tile-large` spans 6, `.tile-medium` spans 4, and `.tile-small` spans 2 so high-density layouts keep visual rhythm.

#### Scenario: Large desktops (1200–1439px)
- **WHEN** the viewport width falls within 1200–1439px
- **THEN** `.tile-large` spans 6 of 12 columns, `.tile-medium` spans 4, `.tile-small` spans 3, and gutters shrink according to the design token scale.

#### Scenario: Tablets (600–1199px)
- **WHEN** the viewport width is between 600 and 1199px
- **THEN** `.tile-large` spans the full width, `.tile-medium` spans 6 of 8 columns above 900px and 4 of 8 columns below, while `.tile-small` displays in two-column grids until <600px.

#### Scenario: Narrow phones (<600px)
- **WHEN** the viewport width is <600px
- **THEN** every tile spans the single column and horizontal scrolling is never required.

### Requirement: Adaptive Header Controls
The dashboard header MUST keep the status info and quick-action buttons accessible on tablets and phones by wrapping/stacking instead of overflowing.

#### Scenario: Tablet header wrap
- **WHEN** the viewport width is between 600px and 899px
- **THEN** the status block sits above the controls and the five action buttons layout as a 2x2 grid (with the fifth button centered on a third row) with at least 16px gaps.

### Requirement: Flexible Tile Heights
High-variance visualization tiles (world map, narrative timeline, performance metrics) MUST scale their heights responsively to avoid cropped content or extreme whitespace on short viewports.

#### Scenario: Map tile adapts to viewport
- **WHEN** the world map tile renders on a 360px-tall mobile viewport
- **THEN** the tile height stays within 45–60% of the viewport height (capping at the desktop max) and maintains full interactivity without overflow scroll bars.

### ADDED Requirements
### Requirement: Tile Elevation & Motion
Dashboard tiles MUST provide consistent elevation states (rest, hover, focus) and a subtle entrance animation so the layout feels polished across breakpoints.

#### Scenario: Hover/focus elevation
- **WHEN** a pointer hovers over or keyboard focuses any `.bento-tile`
- **THEN** the tile raises to the “interactive” elevation token (shadow + scale) while retaining WCAG-compliant outline states.

#### Scenario: Entrance animation
- **WHEN** the dashboard grid mounts or tiles reorder
- **THEN** tiles fade and slide in using the shared animation token, completing within 250ms so motion remains subtle and accessible.
