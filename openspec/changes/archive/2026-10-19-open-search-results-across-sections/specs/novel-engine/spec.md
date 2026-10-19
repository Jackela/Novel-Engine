## ADDED Requirements

### Requirement: Project search result navigation

Selecting a project search result MUST open its Document in the editor and
deliver that result's locate intent, regardless of the current authoring
section. If the current section excludes the target kind, the Studio MUST
switch to the existing Manuscript section while retaining the selected
Inspector. If the current section permits the target, it MUST keep that route.
Ordinary section navigation MUST retain its existing kind constraints.

#### Scenario: A cross-kind result opens from a restricted section

- **GIVEN** Outline, Characters or World is selected and project search returns a Document of another kind
- **WHEN** the author selects that result
- **THEN** the Studio opens the target Document in Manuscript with its current body
- **AND** the selected Inspector is retained and the editor receives the locate term

#### Scenario: A compatible result retains its section

- **GIVEN** the current section permits the search result's Document kind
- **WHEN** the author selects that result
- **THEN** the target body and locate intent reach the editor without changing the section
