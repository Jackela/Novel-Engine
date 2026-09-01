## MODIFIED Requirements

### Requirement: Entry flow session probe
The Studio entry MUST probe the session on mount. A valid session MUST replace
navigation into the project library. HTTP 401 MUST continue to setup-status and
render the unified setup/login form. Network, timeout, contract, and server
failures MUST remain on the entry surface with a readable error and working
Retry action; they MUST NOT be interpreted as an unconfigured owner. The form
prefills the username `author`, enforces the ten-character password minimum,
switches autocomplete between new-password and current-password according to
setup status, exposes exact pending state, and prevents duplicate submission.
Unmount MUST abort cancellable bootstrap reads and late completions MUST neither
publish state nor navigate.

#### Scenario: Valid session skips to the library
- **GIVEN** a valid session exists
- **WHEN** the entry page mounts
- **THEN** navigation replaces into the project library without rendering the form

#### Scenario: First-run single submit sets up and logs in
- **GIVEN** the session probe returns HTTP 401 and no owner is configured
- **WHEN** the author submits the unified form once with valid credentials
- **THEN** the owner is created and the session established in one flow
- **AND** navigation proceeds to the project library
- **AND** duplicate activation cannot start a second setup or login request

#### Scenario: Entry operational failure stays recoverable
- **GIVEN** the session probe fails because of a network, timeout, contract, or server error
- **WHEN** the entry page classifies the failure
- **THEN** it does not request setup status or render a first-run form
- **AND** it presents the readable failure with a working Retry action

### Requirement: Explicit asynchronous operation state
The Studio MUST ensure review, AI proposal and acceptance, export, settings
save, retry, reorder, document creation, project creation, logout, and job
refresh operations expose pending state and prevent duplicate submission while
pending. Only the control that initiated an operation MUST expose its accessible
busy state; related controls MAY be disabled to protect invariants but MUST
retain their normal accessible names. When an operation settles, focus MUST
return to its initiating control only when the author has not deliberately moved
focus elsewhere. If the initiator disappears or becomes unavailable, focus MUST
move to a stable, semantically related fallback. Failures MUST remain readable,
and success MUST clear stale errors and refresh the affected data. A running
whole-book operation MUST keep its Stop control reachable from every Inspector
surface.

#### Scenario: Duplicate submission guard
- **GIVEN** a project creation or export operation is in progress
- **WHEN** the author activates the initiating command again
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

## ADDED Requirements

### Requirement: Recoverable project-library loading
The project library MUST verify the owner session before requesting its project
list. HTTP 401 MUST replace navigation to entry. A project-list network,
timeout, contract, or server failure MUST retain the library route and present a
readable error with a working Retry action. Retry MUST supersede any prior read,
expose pending state, and prevent duplicate requests. Unmount MUST abort
cancellable reads, and late completions from an earlier attempt MUST neither
replace the current list nor navigate.

#### Scenario: Operational project-list failure can be retried
- **GIVEN** the owner session is valid and the project list fails operationally
- **WHEN** the failure is displayed and the author activates Retry
- **THEN** the library route is retained
- **AND** one new project-list request starts with accessible pending state
- **AND** success replaces the error with the current ordered project list

#### Scenario: Authentication failure returns to entry
- **GIVEN** the library session probe returns HTTP 401
- **WHEN** the failure is classified
- **THEN** navigation replaces to the entry route
- **AND** no project-list request starts

#### Scenario: Library unmount cancels reads
- **GIVEN** a session or project-list read is pending
- **WHEN** the library unmounts
- **THEN** the cancellable request is aborted
- **AND** its later completion cannot publish state or navigate
