## ADDED Requirements

> Carried verbatim from the retired `novel-studio` capability per the #254
> cutover resolution: these six pure-frontend Requirements already express
> the retained Studio behavior. The source text is unchanged — only the
> owning capability changes.

### Requirement: Complete single-author Studio
The system MUST provide project library, manuscript, outline, character, world,
review, history, export, and settings surfaces.

#### Scenario: Authoring flow
- **GIVEN** an owner or valid guest project
- **WHEN** the author edits a Markdown document and pauses for 1.5 seconds
- **THEN** the Studio saves a new revision
- **AND** shows saved, saving, or conflict state

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
