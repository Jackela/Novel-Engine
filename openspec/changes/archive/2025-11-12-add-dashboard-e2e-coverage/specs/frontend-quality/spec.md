## ADDED Requirements
### Requirement: Login E2E Coverage
The Playwright suite MUST include a login spec that covers successful authentication, inline error handling, and skip-link focus behavior.

#### Scenario: Successful login
- **GIVEN** valid credentials (or demo mode)
- **WHEN** the E2E spec submits the form
- **THEN** it waits for dashboard navigation and asserts the skip link can move focus to `#main-content`.

#### Scenario: Inline errors
- **GIVEN** invalid credentials
- **WHEN** the spec submits the form
- **THEN** the inline error message appears and the submit button returns to idle state within 5s.

### Requirement: Dashboard Interaction E2E Coverage
The suite MUST exercise major dashboard interactions (map selection, quick actions, pipeline states) on both desktop and tablet viewports.

#### Scenario: Map entity selection
- **WHEN** the spec clicks/activates each map entity
- **THEN** the selected state toggles and the tile status text updates without JS errors.

#### Scenario: Quick action toggles
- **WHEN** the spec triggers Start/Pause/Stop actions
- **THEN** the pipeline tile reflects the state in under 5s and the quick action buttons disable/enable accordingly.
