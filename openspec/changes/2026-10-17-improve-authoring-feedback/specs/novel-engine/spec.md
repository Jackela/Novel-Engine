## ADDED Requirements

### Requirement: Saved-source and completed Review feedback

The Review and Export panels MUST explain that their operations use saved
chapters. While the active chapter's Draft has unsaved title or Markdown
changes, both panels MUST show a non-blocking notice that those changes are
excluded. The notice MUST reflect actual Draft state while saving is waiting,
in flight, failed, or conflicted; a save-status label alone MUST NOT establish
that an edit exists. Saving those changes, reverting to the accepted text, or
changing the active Document or Project MUST reconcile the notice with the
current Draft. Non-chapter Drafts MUST NOT trigger a chapter notice. The notice
MUST NOT initiate a save or introduce a new prerequisite for Review or Export.

A successfully loaded selected Review whose complete detail contains zero
issues MUST display a statement that this Review reported no findings. An
absent Review, pending detail, or failed detail MUST NOT produce that success
statement. The statement MUST describe the selected completed Review rather
than claim that the manuscript is defect-free or that a new pending run has
completed.

#### Scenario: Unsaved chapter edits remain visible across save outcomes

- **GIVEN** the active chapter has unsaved title or Markdown changes
- **WHEN** the author opens Review or Export while saving is waiting, in flight,
  failed, or conflicted
- **THEN** the panel explains its saved-chapter source and the exclusion of
  those unsaved changes
- **AND** that notice neither starts a save nor blocks the existing operation

#### Scenario: Saved or reverted text clears the notice

- **GIVEN** the unsaved-chapter notice is visible
- **WHEN** the current changes are saved or the Draft returns to its accepted
  title and Markdown without remaining unpersisted edits
- **THEN** the notice disappears
- **AND** the permanent explanation of the saved-chapter source remains

#### Scenario: Selection changes retain only the current Draft's notice

- **GIVEN** chapter A has an unsaved-change notice
- **WHEN** the author selects another Document or another Project
- **THEN** the notice reflects only the new active chapter's actual Draft
- **AND** a clean chapter or a non-chapter Document does not inherit A's notice

#### Scenario: A completed Review reports zero findings

- **GIVEN** the selected Review's complete detail has loaded successfully with
  an empty issues array
- **WHEN** its result is displayed
- **THEN** the panel states that this Review reported no findings
- **AND** its existing provenance remains associated with that result

#### Scenario: Missing or unresolved detail is not a zero-finding result

- **GIVEN** no Review exists, or the selected detail is loading or failed
- **WHEN** the Review panel is displayed
- **THEN** its existing empty, loading, or error state remains distinguishable
- **AND** no zero-finding success is inferred from an absent issues list

### Requirement: Recoverable generated-text copy feedback

Copilot and Jobs MUST provide consistent feedback when the author explicitly
copies displayed generated text. Success MUST be reported only after the
Clipboard API resolves successfully. Missing Clipboard API support or a known
browser permission refusal MUST show a readable instruction to copy the text
manually and MUST leave retry available. Unknown failures MUST remain
observable as unexpected errors rather than silently becoming permission
refusals.

Copy feedback MUST belong to the current displayed text and the latest copy
attempt. A successful retry MUST clear an earlier failure. Changing the text
identity MUST clear old feedback, including an A-to-B-to-A change, and a late
outcome for a departed text or superseded attempt MUST NOT replace current
feedback.

#### Scenario: Clipboard access is unavailable or refused

- **GIVEN** Clipboard API support is missing or the browser refuses clipboard
  access through a known permission error
- **WHEN** the author activates Copy in Copilot or Jobs
- **THEN** that surface explains how to copy the displayed text manually
- **AND** Copy remains available for an explicit retry without changing the text

#### Scenario: A later copy succeeds

- **GIVEN** copying the current displayed text previously failed
- **WHEN** the author retries and the Clipboard API resolves successfully
- **THEN** success feedback replaces the failure

#### Scenario: Old copy outcomes cannot follow another text

- **GIVEN** a copy request is pending for displayed text A
- **WHEN** the displayed text changes to B, including a later return to A,
  before the old request settles
- **THEN** the old request cannot publish feedback for the new display
- **AND** only the latest copy attempt for the current display may update it

#### Scenario: Unexpected copy failure stays diagnosable

- **GIVEN** Clipboard API rejects with an unexpected error
- **WHEN** the copy attempt settles
- **THEN** the failure remains observable through the existing unexpected-error
  reporting surface
- **AND** the interface does not claim that copying succeeded

### Requirement: Volume deletion updates project recency

A successful Volume deletion MUST update the Project's modification time
under the existing project clock policy as part of the same successful
outcome. The library's existing recent-project ordering MUST use that updated
time. A refused or rolled-back deletion MUST leave the Project's modification
time unchanged. Existing last-Volume refusal, chapter reassignment, reading
order, and Revision semantics MUST remain intact.

#### Scenario: Deleting a Volume is recent project activity

- **GIVEN** project A was last updated before project B and A has a deletable
  Volume
- **WHEN** the author deletes that Volume at a time later than B's update
- **THEN** A's modification time reflects the deletion
- **AND** the library's recent-project ordering places A ahead of B

#### Scenario: Refusal or rollback does not manufacture activity

- **GIVEN** a Volume deletion is refused or cannot commit successfully
- **WHEN** the author reads the Project again
- **THEN** its modification time is unchanged
- **AND** the failed deletion has not partially changed its Volume structure

### Requirement: Complete saved chapter input for editorial Review

Fresh and retried editorial Review MUST supply the provider with the complete
Markdown of the captured saved chapters, their document and revision
identities, titles, and reading order. All chapter input MUST come from the
same captured source used by the completed Review's Snapshot; later saves
MUST NOT substitute newer prose into that input. Non-chapter documents and
stored document metadata MUST NOT enter the Review prompt.

Chapter payloads MUST be identified and delimited as untrusted manuscript
data rather than instructions. The prompt MUST preserve the complete captured
chapter text through its encoding without silently summarizing, sampling, or
truncating it to fit a capacity limit. Provider failure, finding validation,
Snapshot ownership, and explicit Proposal acceptance MUST retain their
existing contracts.

#### Scenario: Review receives prose and source identity

- **GIVEN** a captured source contains two saved chapters and non-chapter
  documents
- **WHEN** an editorial Review is submitted to the provider
- **THEN** the prompt contains both chapters' complete Markdown, document and
  revision identities, titles, and relative reading order
- **AND** it omits non-chapter content and stored document metadata

#### Scenario: Later edits do not change the reviewed source

- **GIVEN** Review captured chapter revision A
- **WHEN** the chapter is subsequently saved as revision B while Review runs
- **THEN** the provider input and completed Review Snapshot still refer to A
- **AND** unsaved browser Draft text is not substituted into the provider input

#### Scenario: Manuscript text cannot close the untrusted boundary

- **GIVEN** a captured chapter contains text resembling instructions or
  manuscript delimiters
- **WHEN** its Review prompt is assembled
- **THEN** that text remains encoded within the untrusted manuscript payload
- **AND** its original manuscript content remains represented in full

### Requirement: Bounded Review prompt capacity and retry replay

Every editorial Review task MUST contain at most 8,388,608 UTF-8 bytes across
its complete system and final user prompts, including labels, separators,
delimiters, and escaped chapter payloads. This is the existing generation
prompt budget. Assembly MUST refuse before constructing a Provider when the
complete prompt would exceed it, MUST NOT retain an oversized joined prompt,
and MUST NOT truncate manuscript content to fit. The exact byte limit MUST be
admitted by the capacity check.

Capacity refusal MUST use HTTP 422 with code
`GENERATION_CAPACITY_EXCEEDED`, message `Generation capacity exceeded.`, and
details containing only resource `prompt_bytes`, limit `8388608`, and observed
value `8388609`. A fresh Review refusal MUST construct no Provider and leave
no Job, event, usage, Snapshot, assessment, or finding evidence.

When a keyed Review retry has reserved its Job and then exceeds the limit, it
MUST settle exactly that retry as failed with a failed event and a closed
structured `capacity_error` outcome, without Review or usage evidence.
Replaying the same key MUST return the same byte-identical capacity 422
envelope without rereading the manuscript source, rebuilding the prompt,
constructing a Provider, or creating additional Jobs or events. A different
key MUST represent a distinct attempt and MAY read the newly saved manuscript.

#### Scenario: Exact complete-prompt limit is admitted

- **GIVEN** the complete Review system and user prompts total exactly
  8,388,608 UTF-8 bytes
- **WHEN** the prompt is checked
- **THEN** capacity admission succeeds without truncating any chapter

#### Scenario: Multibyte and escaped content count toward the final limit

- **GIVEN** a chapter contains multibyte characters or characters requiring
  escaping in its encoded payload
- **WHEN** the complete Review prompt would exceed 8,388,608 UTF-8 bytes
- **THEN** Review returns the fixed generation-capacity 422 envelope
- **AND** the check counts the final encoded prompt rather than character
  counts or only the raw chapter Markdown

#### Scenario: Fresh over-limit Review has no workflow evidence

- **GIVEN** the complete Review prompt would contain at least 8,388,609 UTF-8
  bytes
- **WHEN** the author requests a fresh Review
- **THEN** the fixed capacity 422 is returned before Provider construction
- **AND** no Job, event, usage, Snapshot, assessment, or findings are recorded

#### Scenario: Keyed Review capacity refusal replays without work

- **GIVEN** a keyed Review retry reserved its Job and failed on prompt capacity
- **WHEN** the same retry key is submitted again, even after manuscript edits
- **THEN** the response is the same byte-identical capacity 422 envelope
- **AND** the original failed retry and failed event remain the only new
  workflow records
- **AND** no source read, prompt assembly, or Provider construction repeats

#### Scenario: A different key can Review a reduced manuscript

- **GIVEN** a keyed Review retry failed on prompt capacity and the author then
  saved a manuscript whose complete prompt fits the limit
- **WHEN** the author retries using a different key
- **THEN** the new attempt may capture that saved source and invoke the provider
- **AND** replay of the earlier key still returns its original capacity refusal
