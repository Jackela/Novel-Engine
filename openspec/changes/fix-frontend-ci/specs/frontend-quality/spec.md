## ADDED Requirements
### Requirement: Accessible Form Labels
Every visible form label in the frontend MUST either wrap its control or reference it via `htmlFor/id` so assistive tech can announce the association and eslint’s `label-has-associated-control` rule stays green.

#### Scenario: Labeled text inputs
- **GIVEN** a form control such as the API key input in `AgentInterface`
- **WHEN** the control renders
- **THEN** the markup includes either `<label><input .../></label>` or matching `id/htmlFor`
- **AND** `npm run lint` reports zero `label-has-associated-control` violations.

### Requirement: Keyboard-Accessible Interactive Elements
Any UI element that handles pointer clicks MUST either be a semantic button/link or expose the correct role, `tabIndex`, and `Enter/Space` key handlers so keyboard and assistive users can trigger it. Non-semantic containers without those affordances are not allowed.

#### Scenario: Clickable dashboard cards
- **GIVEN** a tile (e.g., status rows in `NarrativeDisplay.tsx`) that uses `onClick`
- **WHEN** a keyboard user tabs to it
- **THEN** the element is focusable, announces an appropriate role, and responds to `Enter`/`Space`
- **AND** `npm run lint` no longer reports `click-events-have-key-events` errors.

### Requirement: Quick E2E Smoke Coverage
The repo MUST include a lightweight Playwright spec that exercises a core dashboard happy path and is callable via `npm run test:e2e -- quick-e2e.spec.js`, ensuring CI has a fast smoke gate.

#### Scenario: Smoke command finds tests
- **WHEN** a developer runs `npm run test:e2e -- quick-e2e.spec.js`
- **THEN** Playwright discovers the referenced spec file, executes at least one test that reaches `/dashboard`, and exits 0 on pass (non-zero on failure)
- **AND** CI logs no “No tests found” errors for that command.
