## MODIFIED Requirements
### Requirement: Entity selection reveals context panel
The world map tile MUST expose a visible details panel that updates whenever a character marker is selected so the interaction produces actionable information, and markers MUST be keyboard operable with deterministic aria attributes that convey selection and panel linkage.

#### Scenario: Details render for the active entity
- **GIVEN** the dashboard renders entity markers on the world map
- **WHEN** the user activates (clicks or keyboard-selects) a marker
- **THEN** a details panel becomes visible without leaving the tile
- **AND** it displays the character's name, role/type, status, and key stats pulled from the same dataset
- **AND** only that entity is marked as selected until another selection occurs.

#### Scenario: Keyboard users can inspect the selection
- **GIVEN** a keyboard-only user tabs to a marker
- **WHEN** they press Enter or Space to activate it
- **THEN** the marker exposes `role="button"`, `tabindex="0"`, `aria-selected="true"`, and `aria-controls` referencing the details region
- **AND** the same details panel content updates and focus/ARIA states reflect the new selection without requiring a mouse.

## ADDED Requirements
### Requirement: Character network exposes actionable nodes
Character network cards MUST be reachable via keyboard focus, announce status/trust, and support Enter/Space to open their mini detail row.

#### Scenario: Character cards are operable without a mouse
- **GIVEN** the user tabs through `[data-role="character-networks"]`
- **WHEN** focus lands on a character card
- **THEN** the card element has `role="button"`, `tabindex="0"`, and `aria-pressed`/`aria-expanded` to indicate activation
- **AND** pressing Enter/Space triggers the same handler as clicking.

### Requirement: Timeline nodes are keyboard navigable
Each narrative timeline node MUST participate in a roving tablist so users can inspect current, completed, and upcoming entries with consistent aria metadata.

#### Scenario: Timeline exposes aria-current status
- **GIVEN** focus is inside `[data-role="narrative-timeline"]`
- **WHEN** the user arrows or tabs through timeline nodes
- **THEN** only the active node has `tabindex="0"` (`-1` for others)
- **AND** the current node exposes `aria-current="step"` and Enter/Space triggers the same callbacks used for pointer events.

### Requirement: QuickActions controls are accessible without invalid DOM props
QuickActions controls MUST be keyboard accessible, retain visible focus outlines, and avoid leaking custom props to the DOM.

#### Scenario: QuickActions render without DOM warnings
- **GIVEN** QuickActions render in any state (idle or running)
- **WHEN** React strict-mode checks props
- **THEN** no custom props (e.g., `active`) reach the DOM
- **AND** focus outlines remain visible for keyboard navigation.

### Requirement: Spatial/network tiles consume backend data
World map and character network tiles MUST derive their datasets from the `/characters` API (or shared hook) so UI counts and names can be validated against backend data.

#### Scenario: UI reflects `/characters` payload
- **GIVEN** `/characters` returns `[{ id, name, role, location, trust, status }]`
- **WHEN** the dashboard renders the map and network tiles
- **THEN** every marker/card corresponds to an entry from the payload (matching name + status)
- **AND** badges show totals that equal the number of characters/links supplied, and tests can stub the API to verify the mapping logic.
