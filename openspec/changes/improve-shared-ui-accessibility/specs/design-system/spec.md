## ADDED Requirements
### Requirement: Accessible Form Controls
Shared form primitives (buttons, inputs, banners) MUST preserve focus, announce validation changes, and avoid unintended submissions.

#### Scenario: Deterministic input ids and error messaging
- **GIVEN** a screen renders `<Input label="Agent Name" helperText="Required" />`
- **WHEN** the field re-renders due to validation
- **THEN** the label `for` attribute still matches the input `id`
- **AND** helper/error text references the same `aria-describedby` target with `aria-live="polite"` so screen readers hear state changes.

#### Scenario: Buttons default to safe interactions
- **GIVEN** a `<Button>` is placed inside a form without a `type` prop
- **WHEN** the user clicks it or presses Enter/Space
- **THEN** it behaves as `type="button"` (no accidental submit)
- **AND** focus-visible styling remains at 3:1 contrast even when custom variants/styles are supplied.

### Requirement: Dashboard Loading Feedback
The dashboard MUST provide perceivable loading states for data-driven tiles so users never see empty values without context.

#### Scenario: Skeletons replace placeholder ellipses
- **GIVEN** character, campaign, or system health queries are still loading
- **WHEN** the cards render in the overview grid
- **THEN** each metric slot shows a skeleton placeholder of matching height/width
- **AND** the layout does not shift when data arrives.

#### Scenario: Live loading summary
- **GIVEN** any dashboard query is pending for more than 500ms
- **WHEN** assistive tech scans the page
- **THEN** an `aria-live="polite"` region communicates “Loading dashboard metrics…” until data resolves or an error banner appears with a retry.
