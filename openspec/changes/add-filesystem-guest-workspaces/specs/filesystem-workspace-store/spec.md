## ADDED Requirements

### Requirement: Workspace isolation
The system MUST scope all user-created data to a workspace derived from the current session and MUST NOT allow access across workspaces.

#### Scenario: Two guest sessions are isolated
- **GIVEN** two separate guest sessions exist
- **WHEN** session A creates a character
- **THEN** session B does not see that character when listing its characters.

### Requirement: Durable writes on filesystem
Workspace persistence MUST be stored on the filesystem with atomic write semantics so partial writes do not corrupt data.

#### Scenario: Character write is atomic
- **WHEN** the backend persists a character record to disk
- **THEN** the file is written atomically (temp + rename) so an interruption does not leave a partially-written JSON document.

### Requirement: Workspace schema versioning
Each workspace MUST contain a manifest that records a schema version and supports forward migrations.

#### Scenario: Workspace includes schemaVersion
- **WHEN** a workspace is created on disk
- **THEN** it contains a manifest with `schemaVersion` and timestamps that can be used for migrations and diagnostics.

### Requirement: Workspace export and import
The system MUST support exporting a workspace and importing it into a new session to enable portability.

#### Scenario: Exported workspace can be re-imported
- **GIVEN** a workspace contains at least one character
- **WHEN** the user exports and then imports the workspace
- **THEN** the imported workspace contains the same character data and identifiers (or a documented mapping if IDs are reissued).

