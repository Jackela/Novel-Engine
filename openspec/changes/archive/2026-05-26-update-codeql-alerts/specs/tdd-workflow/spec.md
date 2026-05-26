## ADDED Requirements
### Requirement: Code scanning hygiene gate
The default branch MUST have zero open CodeQL alerts, except those explicitly suppressed with documented justification and scope.

#### Scenario: CodeQL clean on default branch
- **GIVEN** CodeQL has analyzed the default branch
- **WHEN** the code scanning results are reported
- **THEN** there are zero open alerts or each remaining alert is suppressed with a documented justification
- **AND** suppressions are limited to the smallest practical scope (file or block level)

#### Scenario: Suppression requires justification
- **GIVEN** a CodeQL alert is a confirmed false positive or acceptable risk
- **WHEN** a suppression is added
- **THEN** the suppression includes a short rationale and reason category
- **AND** the rationale references the validation performed
