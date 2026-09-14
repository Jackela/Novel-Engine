## ADDED Requirements

### Requirement: Opt-in diagnostics export

The Studio Settings surface MUST offer an explicit "Export diagnostics"
action that, on activation, requests a diagnostics summary from one
owner-guarded read-only endpoint scoped to the current project and saves it
locally as a JSON file with a client-derived name. The summary MUST contain
the product identity and version from the release-version authority, a
runtime environment summary, a configuration summary reporting the resolved
provider selection and the set/unset state of recognized configuration
keys, a recent error summary listing the persisted error messages of the
current project's most recent failed Jobs when any exist, and a database
health summary with the same field family as the `doctor` command
(integrity check, journal mode, foreign-key enforcement, owner status).
The error summary MUST present only what Jobs durably record — the
envelope's error code exists only at HTTP response time and MUST NOT be
invented for the export. Secret values — the session secret and any
provider API key — MUST NOT appear anywhere in the exported file, and
provider failures included in the error summary MUST stay inside the
provider failure diagnostics boundary with no provider response body
exposed. The export MUST NOT include manuscript content, document bodies,
or Lore entries. The action MUST display the diagnostics privacy statement,
generation MUST NOT perform any network activity beyond the Studio's own
read-only endpoint, and the product MUST NOT transmit the exported file
anywhere — where the file goes is the author's decision alone.

#### Scenario: Export contains the support field families

- **GIVEN** an instance with a configured provider and a healthy database
- **WHEN** the author activates "Export diagnostics"
- **THEN** the saved JSON contains the product version, a runtime environment summary, the resolved provider with its label and configured state, the database health fields matching the `doctor` field family, and a generated-at timestamp

#### Scenario: Secrets never appear in the export

- **GIVEN** an instance with a session secret set and a provider API key configured
- **WHEN** the author exports diagnostics
- **THEN** neither the secret nor the API key value occurs anywhere in the serialized file
- **AND** their configuration state is reported only as a configured/set boolean

#### Scenario: Recent errors respect the provider boundary

- **GIVEN** the provider transport receives an error response whose body the provider failure diagnostics boundary discards, and the resulting failure is one of the project's most recent failed Jobs
- **WHEN** the author exports diagnostics
- **THEN** the error summary lists that job's persisted error message
- **AND** the discarded upstream body text does not appear anywhere in the export
- **AND** the summary presents no error code that was not durably recorded

#### Scenario: No errors yields an empty error summary

- **GIVEN** the current project's job history has no failed Jobs
- **WHEN** the author exports diagnostics
- **THEN** the error summary is an explicitly empty state, not an error or a missing field

#### Scenario: The book stays out of diagnostics

- **GIVEN** a project with chapters, character documents, and Lore entries
- **WHEN** the author exports diagnostics
- **THEN** the file contains no document bodies, manuscript text, or Lore content

#### Scenario: Export is strictly local

- **WHEN** the author activates the export
- **THEN** the only network activity is the request to the Studio's own read-only diagnostics endpoint
- **AND** the file is saved through the browser's download mechanism with a client-derived filename
- **AND** the product transmits the file nowhere

#### Scenario: The privacy statement is visible with the action

- **WHEN** the Settings surface renders the export action
- **THEN** the privacy statement is displayed with it, stating that the file stays on the author's computer, contains no writing and no API keys, and is shared only by the author's choice
