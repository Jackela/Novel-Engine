## MODIFIED Requirements

### Requirement: CLI operational surface

The CLI MUST provide four commands. Every command MUST establish the configured
database authority and pass the legacy-sibling ambiguity gate before database
backup, migration, reconciliation, import, or inspection. After that gate
passes, `serve` MUST back up the SQLite store before applying pending
migrations, then start the API. Once listening, the first `SIGINT` or `SIGTERM`
MUST initiate one controlled shutdown. The command MUST await application
resource release, later shutdown signals MUST NOT start a second shutdown
cycle, and the command MUST leave none of its own signal subscriptions on a
terminal path. Controlled shutdown MUST already be available when the listener
becomes reachable. A successful signal shutdown MUST return `130` for `SIGINT`
or `143` for `SIGTERM`; a resource-release failure MUST remain visible and
return `1` instead.

`import` MUST take an explicit source path and owner, run as the owner principal
without HTTP authentication, and print the imported project. `backup` MUST
write a backup and print its path. `doctor` MUST report the version, database
path, integrity check, journal mode, foreign-key enforcement, and owner status,
exiting non-zero unless the integrity check passes and foreign keys are enabled.

#### Scenario: Serve backs up before migrating

- **GIVEN** the database authority and ambiguity gate passes for a database with
  pending migrations
- **WHEN** `serve` runs
- **THEN** a backup is written beneath the backups directory before migrations apply

#### Scenario: SIGINT closes serve once

- **GIVEN** `serve` is listening and owns an open application
- **WHEN** `SIGINT` is the first shutdown signal
- **THEN** application resources are released before the command returns
- **AND** later shutdown signals do not start another shutdown cycle
- **AND** no CLI-owned signal subscription remains
- **AND** the command returns exit code 130

#### Scenario: SIGTERM closes serve once

- **GIVEN** `serve` is listening and owns an open application
- **WHEN** `SIGTERM` is the first shutdown signal
- **THEN** application resources are released before the command returns
- **AND** no CLI-owned signal subscription remains
- **AND** the command returns exit code 143

#### Scenario: Listening has no unowned signal window

- **GIVEN** `serve` is transitioning from startup to a reachable listener
- **WHEN** a shutdown signal arrives at that boundary
- **THEN** the signal is captured by the same controlled shutdown lifecycle
- **AND** application resources are released before the command returns

#### Scenario: Signal resource-release failure remains visible

- **GIVEN** a shutdown signal owns the serve lifecycle
- **WHEN** application resource release fails
- **THEN** the resource-release failure is reported through the CLI error channel
- **AND** no CLI-owned signal subscription remains
- **AND** the command returns exit code 1 rather than the signal code

#### Scenario: CLI import binds to an owner

- **GIVEN** a legacy workspace directory
- **WHEN** `import` runs with the explicit source path and owner name
- **THEN** the project is imported scoped to that owner without HTTP authentication
- **AND** the imported project is printed

#### Scenario: Doctor fails on corruption

- **GIVEN** a corrupted database
- **WHEN** `doctor` runs
- **THEN** the integrity check reports the corruption
- **AND** the exit code is non-zero
