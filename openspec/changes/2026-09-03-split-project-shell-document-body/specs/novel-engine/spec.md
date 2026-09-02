## ADDED Requirements

### Requirement: Bounded project shell and explicit current Document

`GET /api/projects/:projectId` and successful `POST /api/projects` MUST return a
strict project shell containing the existing project scalar fields plus
required ordered `documents` and `volumes`. Each document summary MUST contain
only `id`, `project_id`, `kind`, `title`, `position`, nullable `volume_id`,
nullable `beat_ref`, nullable closed `lore_status`, `current_revision_id`, exact
non-negative `word_count`, `created_at`, and `updated_at`. It MUST NOT contain
`content_markdown`, `metadata`, or `revision_source`; omitted fields MUST NOT be
published as null. Project creation MUST identify its seeded document through
the same summary contract.

`GET /api/projects/:projectId/documents/:documentId` MUST return the existing
strict complete current Document for exactly one project-scoped document,
including its accepted current Markdown, metadata, revision source, current
revision id, and word count. It MUST NOT expose an arbitrary historical
revision. The endpoint MUST authenticate before consulting project, document,
or revision state. After authentication, a missing document, a document under a
different route project, and a document outside the Owner's scope MUST return
the same 404 code, message, and envelope without disclosing which scope failed.

Successful `PUT /api/projects/:projectId/documents/reorder` MUST return the same
ordered document-summary shape and MUST NOT return any document body, metadata,
or revision source. Its existing full-set validation and atomic position rules
remain unchanged.

#### Scenario: Project open returns navigation without manuscript bodies

- **GIVEN** a project contains many Documents with large current Markdown and metadata
- **WHEN** its project detail is requested
- **THEN** the response contains the project scalars, ordered volumes, and ordered document summaries
- **AND** no summary contains `content_markdown`, `metadata`, or `revision_source`
- **AND** every summary carries the current revision id and exact word count

#### Scenario: Project creation returns a bounded seed shell

- **GIVEN** an authenticated Owner creates a project
- **WHEN** project creation succeeds
- **THEN** the response contains the seeded Chapter 1 as a document summary
- **AND** its Markdown body and metadata are not embedded in the project shell

#### Scenario: One current Document is read explicitly

- **GIVEN** a project shell identifies document D and its current revision R
- **WHEN** the Owner requests D through the scoped current-document endpoint
- **THEN** the response is the complete current Document for D at R
- **AND** no sibling Document body is returned
- **AND** no historical revision-detail resource is exposed

#### Scenario: Current-document scope fails without disclosure

- **GIVEN** a document is missing, belongs to another route project, or is outside the Principal's scope
- **WHEN** an authenticated current-document request addresses it
- **THEN** every case returns the same 404 code, message, and body
- **AND** no project, document, revision, or ownership state is disclosed

#### Scenario: Authentication precedes current-document lookup

- **GIVEN** no authenticated Owner session
- **WHEN** any syntactically valid project and document identifiers are requested
- **THEN** the response is 401
- **AND** project, document, and revision storage are not consulted

#### Scenario: Reorder returns structure only

- **GIVEN** a project contains Documents A, B, and C with complete bodies
- **WHEN** the Owner reorders them as C, A, B
- **THEN** the response contains C, A, and B in their committed positions as summaries
- **AND** no body, metadata object, or revision source is returned

### Requirement: Causally owned active Document loading

On an authoring project route, the Studio MUST bootstrap project data by reading
the project shell and at most the selected current Document. It MUST NOT fetch
complete sibling Documents speculatively. An accepted Document held in client
state MUST be used only when its `project_id`, document `id`, and
`current_revision_id` exactly match the active shell summary. A missing or
mismatched accepted Document MUST be fetched through the scoped current-
document endpoint and MUST NOT be rendered as empty content.

Active-document requests MUST be owned by project, document, expected current
revision, and lifecycle. Equal requests MAY coalesce but MUST publish their
outcome to every still-mounted consumer. A project/document switch, newer
expected revision, abort, or unmount MUST prevent a late response from
publishing into current state. The Studio MUST retain no inactive complete-
document body after selection changes. Successful complete-Document mutation
responses MUST advance shell and active body together only when their causal
identity is current; summary-only reorder MUST NOT roll the active body back.

A shell failure MUST expose a recoverable project-surface error. A current-
document failure MUST preserve usable shell navigation and expose an editor-
local readable error and Retry action. Retrying MUST target the shell's current
revision, and a fresher shell pointer MUST supersede the failed expectation.

#### Scenario: Initial authoring load reads only the active body

- **GIVEN** a project shell contains many document summaries and selects D
- **WHEN** the authoring route finishes its initial project-data bootstrap
- **THEN** only D's complete current Document has been requested
- **AND** no sibling body has been requested or retained

#### Scenario: A matching accepted Document may be reused

- **GIVEN** the active state holds D at revision R
- **AND** the current shell summary for D still points to R
- **WHEN** the authoring surface renders D again within the same ownership lifecycle
- **THEN** the accepted Document may be reused without another body read
- **AND** the editor's unsaved Draft is not treated as that accepted Document

#### Scenario: Revision mismatch forces an exact read

- **GIVEN** active accepted state holds D at revision R1
- **AND** a fresh shell points D to revision R2
- **WHEN** D is selected
- **THEN** R1 content is not rendered as current
- **AND** the Studio requests D's current Document for R2 ownership

#### Scenario: Late body cannot cross selection

- **GIVEN** a current-document request for project P1 document D1 is in flight
- **WHEN** the author selects another project or document before it completes
- **THEN** the earlier request is aborted when cancellable
- **AND** any late outcome cannot publish body, pending, success, or error state into the new selection

#### Scenario: Mutation result wins over an older read

- **GIVEN** a body read expects revision R1
- **AND** a successful save publishes the complete Document at revision R2
- **WHEN** the older R1 read completes later
- **THEN** the shell and active accepted Document remain at R2
- **AND** reorder summaries cannot replace R2 with an older body

#### Scenario: Editor failure leaves navigation recoverable

- **GIVEN** the project shell loaded but the selected current Document failed to load
- **WHEN** the failure is presented
- **THEN** document navigation remains usable
- **AND** the editor shows a readable failure with a Retry action instead of an empty Document

### Requirement: Lazy and independent Review and Export hydration

Project bootstrap MUST NOT request Review or Export history until its respective
route-backed Inspector panel is selected. Selecting Review MUST NOT request
Export history, and selecting Export MUST NOT request Review history. Direct
navigation, refresh, Back, and Forward MUST activate only the panel selected by
the URL. This deferred activation MUST NOT change either history's existing
response shape and MUST NOT be represented as pagination or a bounded-history
guarantee.

Project shell, active Document, Review, and Export reads MUST keep independent
pending, success, failure, abort, and retry ownership. A Review failure MUST NOT
clear or block the active Document or Export, and an Export failure MUST NOT
clear or block the active Document or Review. Leaving a panel MUST prevent its
late response from becoming the visible state. Returning to a failed panel MUST
show a readable Retry action rather than an invented empty history.

#### Scenario: Authoring bootstrap does not prefetch histories

- **GIVEN** the author enters a project on an authoring route with the default Inspector panel
- **WHEN** shell and active Document bootstrap completes
- **THEN** neither Review history nor Export history has been requested

#### Scenario: Review activation is isolated

- **GIVEN** neither history has been loaded for the mounted project
- **WHEN** the author selects Review
- **THEN** Review history is requested and exposes its own pending state
- **AND** Export history is not requested

#### Scenario: Export failure does not take down authoring

- **GIVEN** shell and active Document are usable
- **WHEN** the selected Export history request fails
- **THEN** the editor and navigation remain usable
- **AND** Export shows a readable failure and Retry action
- **AND** no Review error or empty Review history is manufactured

#### Scenario: URL navigation activates only its panel

- **GIVEN** Review is selected and has settled
- **WHEN** the author navigates to Export and then uses Back
- **THEN** Export alone is activated while its route is selected
- **AND** Back restores Review without making Export the visible state

## MODIFIED Requirements

### Requirement: In-memory document drafts

An unsaved Draft—edited content, title, and save state—MUST live only in the
currently active editor's component memory and MUST NOT persist per Document
across selection changes, route departure, or page reload. A cached complete
Document represents only a server-accepted revision and MUST NOT store or be
mutated into an unsaved Draft.

After 1.5 seconds without a newer edit, the Studio MUST start the existing
conflict-checked autosave attempt. The debounce bounds when an attempt starts;
it MUST NOT be presented as a guarantee that the Draft is durable, because a
request can fail, conflict, be cancelled, or lose its response. A 409 MUST
retain the local Draft and a separate latest-server baseline while that
Document remains active. The Draft is discarded only by successful acceptance,
an explicit conflict choice that replaces it, deliberate selection of another
Document, route departure, or reload. A late save/conflict outcome MUST NOT
publish into a newly active Document.

#### Scenario: Switching documents discards the draft

- **GIVEN** the active Document has unsaved edits or an unresolved conflict Draft
- **WHEN** the author deliberately switches to another Document
- **THEN** the earlier local Draft is discarded and no client-side Draft copy remains
- **AND** the next Document loads from its accepted current revision
- **AND** a late response for the earlier Document cannot replace the new editor state

#### Scenario: No client-side draft persistence

- **GIVEN** unsaved edits
- **WHEN** the page reloads
- **THEN** the editor loads the last accepted current revision with no Draft recovery

#### Scenario: Debounce starts an attempt but does not claim durability

- **GIVEN** the author stops typing in an unsaved Draft
- **WHEN** 1.5 seconds elapse without a newer edit
- **THEN** the Studio starts a conflict-checked save attempt
- **BUT WHEN** that attempt fails, conflicts, or is cancelled
- **THEN** the product does not claim the Draft was accepted or durable

#### Scenario: Conflict retains the active local Draft

- **GIVEN** autosave receives a revision conflict while the same Document remains active
- **WHEN** the latest server Document is loaded as the conflict baseline
- **THEN** the local Draft remains separately available for the explicit conflict actions
- **AND** neither value silently overwrites the other
