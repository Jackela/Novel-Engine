## ADDED Requirements
### Requirement: Entity selection reveals context panel
The world map tile MUST expose a visible details panel that updates whenever a character marker is selected so the interaction produces actionable information.

#### Scenario: Details render for the active entity
- **GIVEN** the dashboard renders entity markers on the world map
- **WHEN** the user activates (clicks or keyboard-selects) a marker
- **THEN** a details panel becomes visible without leaving the tile
- **AND** it displays the character's name, role/type, status, and key stats pulled from the same dataset
- **AND** only that entity is marked as selected until another selection occurs.

#### Scenario: Keyboard users can inspect the selection
- **GIVEN** a keyboard-only user tabs to a marker
- **WHEN** they press Enter or Space to activate it
- **THEN** the same details panel content updates and focus/ARIA states reflect the new selection without requiring a mouse.

### Requirement: Live telemetry indicator refreshes on a timer
The "Live" header badge MUST pair with a timestamp that refreshes on an interval ≤30s even if no other state changes, and announce updates politely for assistive tech.

#### Scenario: Timestamp updates idly
- **GIVEN** the dashboard remains idle for 60 seconds
- **WHEN** 30 seconds elapse
- **THEN** the timestamp text updates to the current time without a manual refresh
- **AND** the container exposes `aria-live="polite"` so screen readers announce the change without stealing focus.

### Requirement: Single quick-action cluster with run-state summary
Quick-action controls MUST appear once in the dashboard header and be accompanied by a run-state summary tile that mirrors the current pipeline state without duplicating the buttons.

#### Scenario: Run-state tile mirrors controls
- **GIVEN** the header renders Start/Pause/Stop/Refresh buttons
- **WHEN** the dashboard also renders the run-state tile
- **THEN** that tile shows the current pipeline state (e.g., Running, Paused) plus timestamp/phase info but does not introduce duplicate actionable buttons, so keyboard focus order stays concise.
