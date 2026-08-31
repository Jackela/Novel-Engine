## ADDED Requirements

### Requirement: Document-scoped Lore lifecycle editing
The Studio MUST expose Lore lifecycle status editing only for active
`character` and `world` documents. The editor MUST treat `draft`, `stable`,
and `deprecated` as a closed set, MUST scope each unsaved selection and save
operation to the active document identity, and MUST use the server-observed
status as that document's saved baseline.

#### Scenario: Switching Lore documents resets the editor identity
- **GIVEN** document A has an unsaved Lore status selection
- **AND** document B has a different saved Lore status
- **WHEN** the author switches from A to B
- **THEN** the editor immediately shows B's saved status
- **AND** A's unsaved selection cannot be submitted for B

#### Scenario: Lore save completion remains asynchronous
- **GIVEN** the author submits a changed Lore status
- **WHEN** the save request remains pending
- **THEN** the editor remains in its pending state
- **AND** completion-time focus restoration does not run yet
- **WHEN** the save operation settles
- **THEN** pending state clears
- **AND** focus returns to the submitting control if that control is still mounted

#### Scenario: Failed Lore save remains retryable
- **GIVEN** the author submits a changed Lore status
- **WHEN** the save fails
- **THEN** the project retains the prior saved status
- **AND** the attempted selection remains available for another submission
- **AND** the failure is exposed through the Studio error surface
