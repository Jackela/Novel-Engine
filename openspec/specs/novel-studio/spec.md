## Purpose

Define the complete Novel Studio 0.3 product contract. This specification is
the single source of truth for its product boundaries, persistence model,
public behavior, and acceptance scenarios.

## Requirements

### Requirement: One product and version authority
The system MUST define Novel Studio as the only authoring product, MUST read the
product version from `pyproject.toml`, and MUST define product behavior in this
capability specification.

#### Scenario: Derived surfaces report the release version
- **GIVEN** the project version is `0.3.1`
- **WHEN** the API, Studio, logs, monitoring metadata, and OpenAPI are produced
- **THEN** each surface reports `0.3.1`
- **AND** none requires an independent version override

### Requirement: SQLite authoring authority
The system MUST persist projects and Markdown documents in SQLite and MUST keep
every accepted document revision immutable.

#### Scenario: Conflict-checked save
- **GIVEN** a document currently points to revision A
- **WHEN** a client saves Markdown based on revision A
- **THEN** the system creates revision B and advances the document atomically

#### Scenario: Stale save
- **GIVEN** a document currently points to revision B
- **WHEN** a client saves Markdown based on revision A
- **THEN** the system returns HTTP 409
- **AND** no revision is silently overwritten

### Requirement: Complete single-author Studio
The system MUST provide project library, manuscript, outline, character, world,
review, history, export, and settings surfaces.

#### Scenario: Authoring flow
- **GIVEN** an owner or valid guest project
- **WHEN** the author edits a Markdown document and pauses for 1.5 seconds
- **THEN** the Studio saves a new revision
- **AND** shows saved, saving, or conflict state

### Requirement: Explicit AI proposals
AI operations MUST produce proposals and MUST NOT mutate documents until the
author accepts the proposal.

#### Scenario: Accept a proposal
- **GIVEN** an AI proposal based on the current document revision
- **WHEN** the author accepts it
- **THEN** the proposed Markdown is saved as a new revision

### Requirement: Snapshot-bound review and export
Reviews and exports MUST reference immutable project snapshots.

#### Scenario: Multi-format export
- **GIVEN** a project snapshot
- **WHEN** the author exports Markdown, DOCX, and EPUB
- **THEN** all formats contain the same ordered document revisions
- **AND** each export records its snapshot

### Requirement: Durable jobs
Jobs and job events MUST be persisted in SQLite and MUST expose interrupted and
retryable states after process failure.

#### Scenario: Restart recovery
- **GIVEN** a running job has no valid execution lease after startup
- **WHEN** recovery runs
- **THEN** the job is marked interrupted
- **AND** the author may explicitly retry it

### Requirement: Owner and temporary guest isolation
The system MUST support one local owner and 24-hour guest sandboxes.

#### Scenario: Guest expiration
- **GIVEN** a guest session is older than 24 hours
- **WHEN** cleanup runs at startup or on the hourly schedule
- **THEN** its projects, jobs, reviews, and exports are deleted

### Requirement: Read-only legacy import
The system MUST preview and idempotently import legacy file workspaces without
modifying their source directories. Web imports MUST be confined to real
directories beneath `data/imports` and MUST reject absolute paths, traversal,
and symbolic links; the local Owner CLI MAY accept an explicit source path.

#### Scenario: Repeated import
- **GIVEN** a legacy workspace was previously imported
- **WHEN** the same source hash is imported again
- **THEN** the existing imported project is returned
- **AND** no duplicate project is created

### Requirement: Self-hosted single-node operation
The system MUST serve the SPA and API from one deployable service with a
persistent data volume.

#### Scenario: Deep link
- **GIVEN** the service is running
- **WHEN** a browser requests a Studio route directly
- **THEN** FastAPI serves the SPA entry point
- **AND** API and static asset routes remain distinct
