## ADDED Requirements
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
