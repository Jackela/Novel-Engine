## MODIFIED Requirements
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
