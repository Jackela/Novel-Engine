## MODIFIED Requirements
### Requirement: Flow-based Adaptive Zones
The dashboard grid MUST keep its semantic zones (Control, Streams, Signals, Pipeline) aligned with the flow-based layout spec so tiles expand/collapse according to priority rather than duplicating content.
#### Scenario: Control band pinned above fold
- **WHEN** the viewport width is ≥ 768 px
- **THEN** the summary strip and quick-action controls render inside a dedicated control band that spans the full width of the grid (no gaps on desktop/tablet)
- **AND** the band height stays ≤ 240 px because quick actions lay out horizontally (two rows max) instead of forming a vertical tower.

#### Scenario: Unique pipeline tile
- **WHEN** the pipeline zone renders
- **THEN** exactly one `<TurnPipelineStatus>` tile is mounted
- **AND** it shares the same auto-fit flow columns as the Streams/System Signals zones (min column width ≥ 320 px) so tiles no longer stack twice in the same column.

### Requirement: Mobile tabbed flow
The mobile tabbed dashboard MUST prioritize control/pipeline panels while preventing low-priority feeds from dominating the first screen.
#### Scenario: High-priority panels expand
- **WHEN** the mobile/tabbed dashboard renders
- **THEN** the Control/Pipeline panels are allowed to grow vertically to show their content (no hard `max-height: 200px` clamp)
- **AND** low-priority feeds (timeline, analytics) default to collapsed/accordion states to keep scroll lengths manageable.
