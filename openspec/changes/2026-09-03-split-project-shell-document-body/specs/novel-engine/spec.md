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
revision, and lifecycle. Requests with exactly equal project, document,
expected revision, and lifecycle MUST coalesce behind one reference-counted
read and MUST publish their outcome to every still-mounted subscriber. One
subscriber leaving MUST NOT abort a read still owned by another; the last
subscriber release MUST abort it when cancellable and clear its bookkeeping.
Release MUST suppress delivery only to that released subscriber or obsolete
owner; every surviving subscriber MUST still receive the shared outcome. A
project/document switch, newer expected revision, abort, or unmount MUST prevent
a late response from publishing only into the obsolete ownership. The Studio
MUST retain no inactive complete-document body after selection changes.

A current-Document response whose `current_revision_id` differs from its
expected shell pointer MUST NOT be rendered as current. The Studio MUST refresh
the shell once. If that refresh returns project 404, the route MUST replace to
the project library. If the project exists but the Document is absent, the
Studio MUST select the route-compatible fallback or no-Document state and MUST
NOT issue a replacement read for the vanished Document. It MAY accept the
response only if the refreshed summary for the same Document now points to that
response revision. Only when that summary still exists with a different pointer
MUST it issue at most one replacement current-Document read owned by the
refreshed pointer. If the replacement also differs because revisions continue
changing, automatic reads MUST stop, the latest shell MUST remain available,
and the editor MUST show a readable changed-again failure with explicit Retry.
One automatic mismatch cycle MUST therefore contain no more than one shell
refresh and at most one replacement body read.

Successful complete-Document mutation responses MUST advance shell and active
body together only when their causal identity is current. Narrow Lore-status
and beat-association responses MUST retain their existing payloads. A response
whose captured project, Document, and field-specific intent epoch still match
the active shell and latest intent MUST patch only its owned summary field:
`lore_status` from the closed authoritative response value or `beat_ref` from
the successful command's normalized requested value (`null` or its trimmed
non-empty title). A resolved beat response is confirmation/display only and
MUST NOT replace stored-reference authority when concurrent outline change
makes that view null. A response that fails any identity or epoch check MUST be
ignored. Reverse-order same-revision responses MUST NOT overwrite a newer
requested value. Summary-only reorder MUST NOT roll the active body back.

HTTP 401 from any project resource MUST replace to Entry. A shell 404 MUST
replace to the project library. A current-Document 404 MUST first refresh the
shell: a missing project replaces to the library; a removed Document selects
the route-compatible fallback summary or the no-Document editor state; and a
shell that still names the Document retains navigation while exposing a scoped
inconsistency and Retry. Only network, timeout, contract, and server failures
MUST stay on their local shell/editor recovery surface. Retrying MUST target the
shell's current revision, and a fresher shell pointer MUST supersede the failed
expectation.

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

#### Scenario: A raced current response converges through the shell

- **GIVEN** a body request expects D at revision R1
- **WHEN** it returns D at revision R2
- **THEN** R2 is not rendered solely because it was the latest response
- **AND** the Studio refreshes the shell once
- **AND** R2 is accepted only if the refreshed summary points to R2

#### Scenario: A raced response cannot revive a removed Document

- **GIVEN** a body request for D returns an unexpected revision
- **WHEN** the required shell refresh shows the project or D no longer exists
- **THEN** a missing project replaces to the project library
- **AND** a missing D selects the route-compatible fallback or no-Document state
- **AND** no replacement current-Document read is sent for D

#### Scenario: Revision churn stops automatic retry

- **GIVEN** an unexpected body revision caused one shell refresh and one replacement current-Document read
- **WHEN** that replacement also differs from its refreshed expected revision
- **THEN** no further automatic shell or body read starts
- **AND** the latest shell remains visible with a readable changed-again error and explicit Retry

#### Scenario: Equal consumers share one owned read

- **GIVEN** two mounted consumers request the same project, Document, expected revision, and lifecycle
- **WHEN** the current Document is read
- **THEN** exactly one request serves both consumers
- **AND** either outcome is delivered to every still-mounted subscriber
- **AND** one consumer leaving does not abort the surviving consumer's request
- **AND** the released consumer alone receives no later delivery

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

#### Scenario: Reverse narrow responses preserve the newest intent

- **GIVEN** two Lore-status or beat-association writes for the same Document and current revision request different values
- **WHEN** the newer intent succeeds before the older response arrives
- **THEN** the newer response patches only its owned `lore_status` or `beat_ref` summary field after identity validation
- **AND** the older response is ignored and cannot replace the newer field value
- **AND** neither narrow payload is treated as a complete Document

#### Scenario: Concurrent outline rename does not erase the stored beat reference

- **GIVEN** the latest beat command successfully stores the normalized requested title `Storm`
- **AND** a concurrent outline rename makes the response resolve `beat` as null
- **WHEN** the response passes project, Document, and intent-epoch validation
- **THEN** the shell summary patches `beat_ref` to `Storm` from the successful command
- **AND** the null display resolution does not rewrite the stored reference to null

#### Scenario: Editor failure leaves navigation recoverable

- **GIVEN** the project shell loaded but the selected current Document failed to load
- **WHEN** the failure is presented
- **THEN** document navigation remains usable
- **AND** the editor shows a readable failure with a Retry action instead of an empty Document

#### Scenario: Missing current Document refreshes structural authority

- **GIVEN** the shell selected D but its current-Document request returns 404
- **WHEN** the Studio refreshes the shell
- **THEN** a missing project replaces to the project library
- **AND** a removed D selects the route-compatible fallback or no-Document state
- **AND** a shell still naming D keeps navigation visible with a scoped Retry failure

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

HTTP 401 from any of these resources MUST replace to Entry rather than remain a
panel-local error. A shell 404 MUST replace to the project library. A Review or
Export 404 MUST first refresh the shell so a missing project navigates to the
library and a still-existing project classifies the impossible scoped miss as a
panel-local contract failure.
Only network, timeout, contract, and server failures remain local operational
recovery states.

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

### Requirement: Project-scoped Studio resource lifecycle

The complete Studio workbench state MUST be owned by the current route
`projectId`. When that identity changes, data and pending state from the prior
project MUST become non-interactive immediately. Shell, active Document, Jobs,
Usage, search, Drafts, revisions, proposals, whole-book progress, Reviews,
Exports, settings, and errors MUST reset or remain keyed to their originating
project and resource owner. A late response from an earlier project, Document,
revision expectation, lifecycle, or field-specific mutation intent MUST NOT
overwrite the active Document, surface, error, revision baseline, Lore status,
or beat association.

Transports that support cancellation MUST be aborted when their last owner
releases them. Exact project/Document/expected-revision/lifecycle reads MUST
coalesce for all subscribers, so one subscriber leaving MUST NOT abort a request
still owned by another. When a non-cancellable mutation has already committed,
the Studio MUST reconcile that result into the originating project/Document
identity (or refresh it from the server) without applying it to the active
Document. Returning to that identity MUST use the committed revision or a newer
server revision as its baseline.

A deliberate Document switch MUST discard an edited local Draft that has not
been accepted, including an unresolved conflict Draft; it MUST NOT persist that
Draft by inactive Document. Accepted server content MAY be recovered from the
current-Document resource but MUST NOT be described as Draft survival. A
conflicted Draft remains available only while its Document stays active or
until the author chooses an explicit conflict action.

#### Scenario: Switching projects hides the previous aggregate immediately

- **GIVEN** project A is visible and project B starts loading
- **WHEN** the route project identity changes from A to B
- **THEN** project A and its actions are no longer rendered
- **AND** only project B may replace the loading state or publish a load error

#### Scenario: Late document completion is discarded

- **GIVEN** a save, restore, search, proposal, body, Lore-status, or beat request belongs to an earlier project, Document, revision, or intent
- **WHEN** it completes after the active ownership changed
- **THEN** its server result does not replace the active identity's Draft, accepted body, revision baseline, field value, result list, or error state
- **AND** a stale shell or body response does not replace current resource state

#### Scenario: A committed inactive-document mutation is reconciled

- **GIVEN** a save, restore, or proposal acceptance for Document A commits after the author selects Document B
- **WHEN** the author later returns to Document A
- **THEN** Document B was never overwritten by A's completion
- **AND** Document A reflects the committed server revision or a newer refreshed revision
- **AND** the next save for A uses that revision as its base

#### Scenario: An unpersisted draft does not survive document navigation

- **GIVEN** the author edits Document A and selects Document B before the save debounce elapses
- **WHEN** the author returns to Document A
- **THEN** A's unpersisted local Draft is absent rather than restored from inactive client state
- **AND** A loads its last accepted current revision or a newer committed revision
- **AND** B never displays or persists A's Draft

#### Scenario: An old export owner cannot trigger a download

- **GIVEN** an Export for project A is waiting for its artifact or download
- **WHEN** the route switches to project B or the workbench unmounts
- **THEN** every cancellable remaining request without another subscriber is aborted
- **AND** no catalog, error, pending state, object URL, or synthetic download from A is published into B

#### Scenario: A stale restore baseline remains recoverable

- **GIVEN** a revision restore uses a base revision that changed while its Document remains active
- **WHEN** the server rejects the restore with HTTP 409
- **THEN** the Studio retains the active local Draft and marks it conflicted
- **AND** refreshes the latest revision baseline without silently overwriting local text
- **AND** a subsequent explicit restore retry uses that refreshed base revision

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

### Requirement: Recoverable project loading

Initial Studio loading MUST classify each resource failure without hiding it or
collapsing independent reads into one aggregate. The project shell MUST load
first; the route-compatible active current Document and the selected lazy
Review or Export panel MAY then load under their own pending, error, lifecycle,
and Retry owner. Retrying one failed resource MUST NOT restart, clear, or block
another successful or pending resource.

An HTTP 401 from shell, current Document, Review, or Export MUST replace to the
entry route. A shell 404 MUST replace to the project library. A current-Document
404 MUST refresh the shell once: a missing project replaces to the library, a
removed active Document selects the route-compatible fallback (or the explicit
no-Document editor state), and a shell that still names the Document retains
navigation with a scoped contract inconsistency and Retry. A Review or Export
404 MUST also refresh the shell before choosing library navigation or, when the
project still exists, a panel-scoped contract failure. Network, timeout,
contract, and server failures MUST retain
the requested Studio URL and display a readable error with working Retry and
Back to projects actions in the resource's own surface.

Retry MUST expose pending state, prevent duplicate requests for that same
resource owner, and retain its recovery surface until it succeeds or navigation
classifies a 401/404. Retry success MUST clear only that owner's stale error and
publish only the corresponding shell, current Document, Review, or Export
state. It MUST move focus to that resource's stable Studio heading only when the
author has not moved focus elsewhere.

#### Scenario: Operational failure can be retried

- **GIVEN** an initial shell, active-Document, Review, or Export request fails with a network or server error
- **WHEN** the failure is displayed and the author activates that resource's Retry
- **THEN** the requested Studio URL is retained
- **AND** one replacement request starts only for the failed resource
- **AND** Retry exposes pending state until that request settles
- **AND** success replaces only that resource's error while preserving the other resource states

#### Scenario: Authentication and absence navigate deliberately

- **GIVEN** project loading returns HTTP 401 or a project-shell HTTP 404
- **WHEN** the failure is classified
- **THEN** 401 from any project resource replaces to the entry route
- **AND** a shell 404 replaces to the project library
- **AND** a current-Document, Review, or Export 404 refreshes shell authority before any local recovery

#### Scenario: Active Document absence selects from the refreshed shell

- **GIVEN** the selected current Document returns 404 while the project route remains active
- **WHEN** the one shell refresh succeeds
- **THEN** a removed Document is replaced by the route-compatible fallback or no-Document state
- **AND** a still-listed Document retains shell navigation with a scoped Retry error
- **AND** no empty Document is invented

#### Scenario: Independent Retry does not rebuild an aggregate

- **GIVEN** the shell and active Document succeeded while the selected Review request failed
- **WHEN** the author retries Review
- **THEN** neither shell nor current Document is requested again solely because of that Retry
- **AND** Export is not requested
- **AND** Review success clears only the Review error

## REMOVED Requirements

### Requirement: Project-scoped Studio lifecycle
