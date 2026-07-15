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

#### Scenario: Reject an invalid proposal acceptance
- **GIVEN** an AI proposal job failed or contains no proposed Markdown
- **WHEN** the author attempts to accept it
- **THEN** the system rejects the acceptance
- **AND** no document revision is created

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

### Requirement: Route-driven project surfaces
The Studio MUST expose review, history, export, and settings as distinct
project-level routes and panels. History MUST contain revision history only;
export MUST contain format selection, export status, and recent export results.
Top-level navigation MUST NOT duplicate these actions in a second menu.

#### Scenario: Navigate to export without changing history
- **GIVEN** an author is viewing a project
- **WHEN** the author navigates to the Export route
- **THEN** the Export panel is rendered as the active project surface
- **AND** the History panel is not rendered as a substitute
- **AND** export format, pending, success, and failure states remain visible

#### Scenario: Navigate to history
- **GIVEN** a project has immutable revisions
- **WHEN** the author navigates to the History route
- **THEN** only revision history and revision actions are shown
- **AND** no export form is required to inspect revisions

### Requirement: Editor-first responsive and touch layout
The Studio MUST use an editor-first single-column layout from 821px through
949px (inclusive), and MUST retain the editor-first order on smaller screens.
Navigation and Inspector regions MUST be collapsible through accessible
controls. No supported viewport may produce horizontal overflow. Interactive
icon and reorder controls MUST provide at least a 44px by 44px target.

#### Scenario: Tablet editor priority
- **GIVEN** the viewport width is 900px
- **WHEN** the Studio renders a project
- **THEN** the editor appears before collapsed navigation and Inspector regions
- **AND** the document content has no horizontal overflow

#### Scenario: Accessible collapsible regions
- **GIVEN** navigation or Inspector is collapsed
- **WHEN** the author activates its toggle
- **THEN** the region expands or collapses
- **AND** the toggle exposes its state with an accessible name and expanded value

### Requirement: APG-compliant Inspector tabs
Inspector tabs MUST implement the WAI-ARIA tabs pattern with one tab stop,
`tablist`, `tab`, and `tabpanel` roles, `aria-selected`, `aria-controls`, and
`aria-labelledby` relationships. Left and right arrows MUST move between tabs;
Home and End MUST select the first and last tab; focus MUST move to the newly
selected tab.

#### Scenario: Keyboard tab navigation
- **GIVEN** focus is on the active Inspector tab
- **WHEN** the author presses ArrowRight, ArrowLeft, Home, or End
- **THEN** the corresponding tab becomes active and selected
- **AND** the associated panel is exposed while other panels are hidden
- **AND** no more than one tab participates in the tab sequence

### Requirement: Explicit asynchronous operation state
The Studio MUST ensure review, AI proposal and acceptance, export, settings
save, retry, reorder, document creation, and job refresh operations expose
pending state,
prevent duplicate submission while pending, and set an accessible busy or
disabled state on the initiating control. Failures MUST remain readable and
success MUST clear stale errors and refresh the affected data.

#### Scenario: Duplicate submission guard
- **GIVEN** an export operation is in progress
- **WHEN** the author activates Export again
- **THEN** the second submission is ignored or prevented
- **AND** the initiating control remains disabled and exposes its pending state

#### Scenario: Failed operation recovery
- **GIVEN** a retryable operation fails
- **WHEN** the failure is presented
- **THEN** a readable error is retained and focus returns to the initiating
  control
- **AND** a subsequent retry can be initiated after pending state clears

### Requirement: Recoverable document save conflicts
When a document save returns HTTP 409, the Studio MUST retain the local draft,
load the latest server document as a separate conflict baseline, and present
two explicit actions: load latest and discard the local draft, or keep the
local draft and retry an overwrite using the latest revision as its baseline.

#### Scenario: Load latest conflict resolution
- **GIVEN** a local draft conflicts with a newer server revision
- **WHEN** the author chooses Load latest
- **THEN** the local draft is discarded
- **AND** the editor adopts the latest server content and revision

#### Scenario: Keep local conflict resolution
- **GIVEN** a local draft conflicts with a newer server revision
- **WHEN** the author chooses Keep local and retry overwrite
- **THEN** the local content is retained
- **AND** the save is retried against the latest revision explicitly

### Requirement: Snapshot-protected deletion conflict
The system MUST reject deletion of a document referenced by an immutable review
or export snapshot with HTTP 409. The database `ON DELETE RESTRICT` invariant
MUST remain in force, and the snapshot and revisions MUST remain intact after a
rejected deletion.

#### Scenario: Delete a snapshotted document
- **GIVEN** a document is referenced by a review or export snapshot
- **WHEN** a client requests document deletion
- **THEN** the API returns HTTP 409 with a stable conflict error
- **AND** no snapshot, revision, or document data is removed

### Requirement: Untrusted AI manuscript boundary
AI manuscript content MUST be serialized as a clearly delimited structured
JSON data block marked untrusted in the prompt. System instructions MUST state
that manuscript content is data and MUST NOT be executed as instructions.
Instruction sanitization and output Markdown sanitization MUST remain separate
defense layers, and the public request/response payload MUST remain unchanged.

#### Scenario: Manuscript prompt injection
- **GIVEN** manuscript text contains instruction-like content
- **WHEN** an AI proposal is requested
- **THEN** the provider receives the manuscript only inside the untrusted JSON
  boundary
- **AND** the system instruction directs the provider not to follow it
- **AND** the API response shape is unchanged

### Requirement: Validation log redaction
Validation error logs MUST contain only the request path, HTTP method, field,
error type, and human-readable message. Raw validation structures and input
values MUST NOT be logged, while the existing client error response contract
remains unchanged.

#### Scenario: Sensitive validation input
- **GIVEN** a validation failure contains a password, token, or API key value
- **WHEN** the error is logged
- **THEN** the log contains only the whitelist fields
- **AND** the sensitive input value is absent from the log record

### Requirement: HMAC-derived session tokens
Session token hashes MUST use HMAC-SHA256 derived from the injected
`SECURITY_SECRET_KEY`; application services MUST receive the secret through
the service registry rather than reading settings directly. Rotating the
secret MUST invalidate all existing sessions and require users to log in again.
Cookie, API, and CSRF external shapes MUST remain unchanged.

#### Scenario: Session verification with stable key
- **GIVEN** a session was created with secret key K
- **WHEN** it is verified with the same key K
- **THEN** the session authenticates normally

#### Scenario: Secret rotation
- **GIVEN** a session was created with secret key K1
- **WHEN** deployment rotates the configured key to K2
- **THEN** the old session is rejected
- **AND** the user must authenticate again
- **AND** cookie, API, and CSRF response shapes are unchanged
