## MODIFIED Requirements

### Requirement: Explicit asynchronous operation state
The Studio MUST ensure review, AI proposal and acceptance, export, settings
save, retry, reorder, document creation, and job refresh operations expose
pending state and prevent duplicate submission while pending. Only the control
that initiated an operation MUST expose its accessible busy state; related
controls MAY be disabled to protect invariants but MUST retain their normal
accessible names. When an operation settles, focus MUST return to its initiating
control only when the author has not deliberately moved focus elsewhere. If the
initiator disappears or becomes unavailable, focus MUST move to a stable,
semantically related fallback. Failures MUST remain readable, and success MUST
clear stale errors and refresh the affected data. A running whole-book operation
MUST keep its Stop control reachable from every Inspector surface.

#### Scenario: Duplicate submission guard
- **GIVEN** an export operation is in progress
- **WHEN** the author activates Export again
- **THEN** the second submission is ignored or prevented
- **AND** the initiating control remains disabled and exposes its pending state

#### Scenario: Failed operation recovery
- **GIVEN** a retryable operation fails
- **WHEN** the failure is presented
- **THEN** a readable error is retained and focus returns to the initiating
  control when the author has not moved focus elsewhere
- **AND** a subsequent retry can be initiated after pending state clears

#### Scenario: Exact pending initiator
- **GIVEN** an author starts adding a chapter while other add and reorder controls are visible
- **WHEN** the request remains pending
- **THEN** only the activated add control exposes an accessible busy state
- **AND** duplicate or conflicting commands cannot start
- **AND** unrelated controls are not announced as if they initiated the request

#### Scenario: Focus does not override deliberate navigation
- **GIVEN** an operation is pending and the author moves focus to another control
- **WHEN** the operation settles
- **THEN** the Studio leaves focus on the author's chosen control

#### Scenario: Removed initiator has a stable focus fallback
- **GIVEN** an operation removes or disables its initiating control when it settles
- **WHEN** focus restoration runs
- **THEN** focus moves to the nearest stable control for the same workflow
- **AND** focus does not fall back to the document body

#### Scenario: Whole-book stop remains reachable
- **GIVEN** whole-book generation is running
- **WHEN** the author switches to any Inspector surface
- **THEN** current progress and Stop remain visible and keyboard reachable

### Requirement: Route-driven project surfaces
The Studio MUST expose review, history, export, and settings as distinct
project-level routes and panels. The URL MUST be the only owner of the visible
Inspector selection: review, history, and export use their project path;
Copilot, Jobs, and Usage use a validated query value on an authoring path, with
Copilot as the query-free default. Clicking or keyboard-activating an Inspector
tab MUST update the URL, and direct navigation, refresh, Back, and Forward MUST
restore the same selected tab and panel. History MUST contain revision history
only; export MUST contain format selection, export status, and recent export
results. Contextual Lore editing MUST appear only with the authoring Copilot
panel. Top-level navigation MUST NOT duplicate these actions in a second menu.

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
- **AND** no export form or Lore status form is present

#### Scenario: Inspector activation is URL-backed
- **GIVEN** the author is on the Review route
- **WHEN** the author clicks History or activates it with an Inspector arrow key
- **THEN** the URL changes to the History route
- **AND** History becomes the selected tab and visible panel
- **AND** Back restores Review as the selected tab and visible panel

### Requirement: Whole-book generation loop
The Studio MUST offer a whole-book generation mode driven by the frontend over
the existing proposal and accept endpoints: it drafts a proposal for the next
chapter needing one, accepts it automatically, and proceeds in reading order.
The loop MUST be stoppable and resumable. Stop or a project-identity change
MUST abort an in-flight proposal before it lands a job or usage event, MUST
prevent any later chapter from starting, and MUST preserve every acceptance
that already completed. An atomic acceptance already executing MAY complete;
if it does, that chapter is counted as preserved completed work.

#### Scenario: The loop advances chapter by chapter
- **GIVEN** a project with an outline and one completed chapter
- **WHEN** the whole-book loop runs
- **THEN** each subsequent chapter receives a generated proposal that is accepted automatically in reading order

#### Scenario: Stop preserves completed work
- **GIVEN** the loop has accepted two chapters and is drafting the next
- **WHEN** the author stops the loop
- **THEN** the two accepted chapters remain
- **AND** the in-flight draft persists no job or usage event
- **AND** no later chapter starts

## REMOVED Requirements

### Requirement: Silent project entry fallback

## ADDED Requirements

### Requirement: Recoverable project loading
Initial Studio loading MUST classify failures rather than hiding every failure.
An unauthenticated response MUST replace to the entry route; a missing project
MUST replace to the project library; network, timeout, and server failures MUST
retain the requested Studio URL and display a readable error with working Retry
and Back to projects actions. Retry MUST expose pending state, prevent duplicate
requests, and retain the recovery surface until it succeeds. Retry success MUST
clear the stale error, publish one complete project, review, and export aggregate,
and move focus to a stable Studio heading only when the author has not moved focus
elsewhere.

#### Scenario: Operational failure can be retried
- **GIVEN** an initial project aggregate request fails with a network or server error
- **WHEN** the failure is displayed and the author activates Retry
- **THEN** the requested Studio URL is retained
- **AND** a new complete aggregate request starts
- **AND** Retry exposes pending state until that request settles
- **AND** success replaces the error with the requested project

#### Scenario: Authentication and absence navigate deliberately
- **GIVEN** initial loading returns HTTP 401 or HTTP 404
- **WHEN** the failure is classified
- **THEN** 401 replaces to the entry route
- **AND** 404 replaces to the project library

### Requirement: Project-scoped Studio lifecycle
The complete Studio workbench state MUST be owned by the current route
`projectId`. When that identity changes, data and pending state from the prior
project MUST become non-interactive immediately. Jobs, usage, search, drafts,
revisions, proposals, whole-book progress, reviews, exports, settings, and
errors MUST reset or remain keyed to their originating project. A late response
from an earlier project or document MUST NOT overwrite the active document,
surface, error, or revision baseline. Transports that support cancellation MUST
be aborted when their owner changes. When a non-cancellable mutation has already
committed, the Studio MUST reconcile that result into the originating
project/document identity (or refresh it from the server) without applying it to
the active document. Returning to that identity MUST use the committed revision
as its baseline. A document switch MUST retain an edited local draft that has not
yet been persisted.

#### Scenario: Switching projects hides the previous aggregate immediately
- **GIVEN** project A is visible and project B starts loading
- **WHEN** the route project identity changes from A to B
- **THEN** project A and its actions are no longer rendered
- **AND** only project B may replace the loading state or publish a load error

#### Scenario: Late document completion is discarded
- **GIVEN** a save, restore, search, or proposal request belongs to an earlier project or document
- **WHEN** it completes after the active identity changed
- **THEN** its server result does not replace the active identity's draft, revision baseline, result list, or error state
- **AND** a stale read response does not replace the current project aggregate

#### Scenario: A committed inactive-document mutation is reconciled
- **GIVEN** a save, restore, or proposal acceptance for document A commits after the author selects document B
- **WHEN** the author later returns to document A
- **THEN** document B was never overwritten by A's completion
- **AND** document A reflects the committed server revision or a newer refreshed revision
- **AND** the next save for A uses that revision as its base

#### Scenario: An unpersisted draft survives document navigation
- **GIVEN** the author edits document A and selects document B before the save debounce elapses
- **WHEN** the author returns to document A
- **THEN** A's local edited text remains present
- **AND** B never displays or persists A's draft

#### Scenario: An old export owner cannot trigger a download
- **GIVEN** an export for project A is waiting for its artifact or download
- **WHEN** the route switches to project B or the workbench unmounts
- **THEN** every cancellable remaining request is aborted
- **AND** no catalog, error, pending state, object URL, or synthetic download from A is published into B

#### Scenario: A stale restore baseline remains recoverable
- **GIVEN** a revision restore uses a base revision that changed while another document was active
- **WHEN** the server rejects the restore with HTTP 409
- **THEN** the Studio retains the local draft and marks it conflicted
- **AND** refreshes the latest revision baseline without silently overwriting local text
- **AND** a subsequent explicit restore retry uses that refreshed base revision
