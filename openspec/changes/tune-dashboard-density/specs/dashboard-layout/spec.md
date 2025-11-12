## ADDED Requirements
### Requirement: Density-aware Zones
Dashboard zones MUST expose semantic density states so the UI can tighten spacing and typography when content volume spikes without sacrificing accessibility.

#### Scenario: Density attributes emitted
- **GIVEN** the dashboard renders any zone (Control, Streams, Signals, Pipeline)
- **WHEN** the underlying data exceeds the configured threshold (e.g., >6 activity entries, queue length >3)
- **THEN** the zone container sets `data-density="compact"` (otherwise `"relaxed"`) and exposes an optional `data-volume` describing the trigger (e.g., `"high-activity"`)
- **AND** child components adjust padding/typography accordingly so buttons remain ≥44px touch targets even in compact mode.

#### Scenario: Streams overflow handling
- **GIVEN** the Streams zone enters `data-density="compact"`
- **WHEN** activity/events exceed the relaxed capacity
- **THEN** the panel enables internal scroll or virtualization, shows a visible overflow affordance (e.g., “View more”), and prevents the zone from pushing lower sections off-screen.

#### Scenario: Signals & Control alignment
- **GIVEN** the Control or Signals zone enters compact density
- **WHEN** quick actions or metric chips render
- **THEN** typography scales down (per design tokens), run summaries collapse to single-line badges, and spacing adjusts while preserving WCAG minimums.
