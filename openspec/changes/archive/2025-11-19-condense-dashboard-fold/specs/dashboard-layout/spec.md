## MODIFIED Requirements
### Requirement: Responsive Bento Grid Layout
- **ADDITION**: Control cluster (summary + quick actions) MUST share a single row that does not exceed 180px height on desktop/tablet. `data-role="control-cluster"` wraps both KPI cards and action buttons so automation treats them as one zone.

#### Scenario: Compressed control band
- **GIVEN** the viewport width is ≥ 768px
- **WHEN** the dashboard renders the control band
- **THEN** Summary KPIs and quick-action buttons reside inside one `data-role="control-cluster"` container laid out with `grid-template-columns` (minmax 160px, auto-fit)
- **AND** the band height does not exceed 180px, with buttons right-aligned and no duplicate connection indicator tiles.

### Requirement: Zone-based Responsive Layout
- **ADDITION**: Desktop first fold MUST include both Streams and Pipeline zones directly beneath the control band, ahead of the Spatial/Backlog zones.

#### Scenario: First fold telemetry density
- **GIVEN** the viewport width is ≥ 1200px
- **WHEN** the dashboard renders the row under the control band
- **THEN** Activity Stream (`data-role="stream-feed"`) and Turn Pipeline (`data-role="pipeline"`) occupy that row, ensuring users see live telemetry without scrolling
- **AND** Spatial tiles (WorldStateMap, CharacterNetworks) share the same fold by capping map height at ≤420px so at least two zones remain visible above the fold.

### Requirement: Semantic Zone Markers
- **ADDITION**: Streams and Pipeline zones MUST expose condensed-mode attributes so tests can distinguish desktop density changes.

#### Scenario: Streams condensed marker
- **GIVEN** the viewport width is ≥ 1200px
- **WHEN** Activity Stream renders the condensed two-column layout
- **THEN** the zone root provides `data-density="condensed"` and each entry exposes deterministic selectors so automation can verify the first fold density target.
