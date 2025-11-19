## MODIFIED Requirements
### Requirement: Entity selection reveals context panel
- **ADDITION**: Spatial markers must expose roving-tabindex keyboard semantics and deterministic aria attributes.

#### Scenario: Map markers support Space/Enter activation
- **GIVEN** focus is on any world-map marker (`data-role="hero-map" [data-location]`)
- **WHEN** the user presses Enter or Space
- **THEN** that marker toggles `aria-selected="true"`, the location list expands (EXACTLY once), and previously selected markers clear their selection state
- **AND** the marker exposes `role="button"`, `tabindex="0"`, and `aria-controls` referencing the details region so assistive tech can follow the context change.

### Requirement: Character network exposes actionable nodes
- **ADDITION**: Character cards must be reachable via keyboard focus, announce status/ trust, and support Enter/Space to open their mini detail row.

#### Scenario: Character cards are operable without a mouse
- **GIVEN** the user tabs through `[data-role="character-networks"]`
- **WHEN** focus lands on a character card
- **THEN** the card element has `role="button"`, `tabindex="0"`, `aria-pressed`/`aria-expanded` to indicate activation, and pressing Enter/Space fires the same handler as clicking.

### Requirement: Timeline nodes are keyboard navigable
- **ADDITION**: Each timeline node participates in a roving tablist so users can inspect `current`, `completed`, and `upcoming` entries with consistent aria metadata.

#### Scenario: Timeline exposes aria-current status
- **GIVEN** focus is inside `[data-role="narrative-timeline"]`
- **WHEN** the user arrows/ tabs through timeline nodes
- **THEN** only the active node has `tabindex="0"` (`-1` for others), the `current` node exposes `aria-current="step"`, and Enter/Space triggers the same callbacks used for pointer events.

### Requirement: Live telemetry indicator refreshes on a timer
- **ADDITION**: QuickActions/summary controls must not emit console warnings due to invalid DOM props and must present visible focus outlines.

#### Scenario: QuickActions render without DOM warnings
- **GIVEN** QuickActions render in any state (idle/running)
- **WHEN** React strict-mode checks props
- **THEN** no custom props (e.g., `active`) reach the DOM, focus outlines remain visible for keyboard navigation, and connection state text (`data-testid="live-indicator"`) updates via `aria-live="polite"` without duplicate announcements.

### Requirement: Spatial/network tiles consume backend data
- **ADDITION**: World map + Character Networks MUST derive their datasets from the `/characters` API (or shared hook) so UI counts/names can be validated against backend data.

#### Scenario: UI reflects `/characters` payload
- **GIVEN** `/characters` returns `[{ id, name, role, location, trust, status }]`
- **WHEN** the dashboard renders the map and network tiles
- **THEN** every marker/card corresponds to an entry from the payload (matching name + status), badges show totals that equal the number of characters/links supplied, and tests can stub the API to verify the mapping logic.
