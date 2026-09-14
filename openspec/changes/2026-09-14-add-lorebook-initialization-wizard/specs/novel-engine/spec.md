## ADDED Requirements

### Requirement: Guided lorebook initialization

The Studio MUST offer a project-scoped lorebook initialization wizard that
turns draft material the author already has into candidate Lore entries
through a configured provider. The wizard MUST accept text the author
pastes and content of already-existing project documents as extraction
input, and MUST present extraction results as candidates — each carrying a
document kind limited to `character` or `world`, a title, suggested aliases,
and a summary body — that are suggestions, not persisted content. Until the
author explicitly confirms, the wizard MUST NOT create any document,
revision, or Lore lifecycle state, and abandoning the wizard MUST leave the
project's lorebook unchanged. On confirmation, each selected candidate MUST
be created through the existing lorebook document creation path with
lifecycle status `draft`, and the wizard MUST report each candidate's
creation result independently. With the trial (mock) provider the wizard
MUST still produce deterministic placeholder candidates and MUST label the
session with the trial-mode wording used by the first-run explainer.

Wizard input MUST be bounded: each input segment MUST be capped in Unicode
code points, the assembled extraction prompt MUST be capped in UTF-8 bytes
under the same authority as proposal generation, and over-budget input MUST
fail closed with a stable capacity error before any provider construction —
never through silent truncation. Multiple input segments MUST each be
extracted within their own budget and their candidates MUST merge into one
deterministically ordered list with same-kind, same-title candidates
collapsed to one candidate carrying the union of suggested aliases. Every
wizard extraction MUST run as a Job under the synchronous job execution
model and MUST record usage under the usage accounting rules. Any retrieval
the wizard performs over project content MUST go through the strict-token
reduction and parameterized full-text search; the wizard MUST NOT construct
SQL or FTS5 expressions by string concatenation.

#### Scenario: Draft material yields candidates

- **GIVEN** a project with a real provider configured
- **WHEN** the author pastes a draft excerpt and runs extraction
- **THEN** the wizard presents candidate entries of kind `character` or `world`, each with a title, suggested aliases, and a summary body
- **AND** no document, revision, or Lore lifecycle state exists yet

#### Scenario: Trial provider yields labeled placeholder candidates

- **GIVEN** a project still on the built-in trial provider
- **WHEN** the author runs the wizard end to end
- **THEN** deterministic placeholder candidates are presented
- **AND** the session is labeled with the trial-mode wording so the author knows real extraction requires a configured provider

#### Scenario: Nothing persists before confirmation

- **GIVEN** the wizard has presented candidates from a completed extraction
- **WHEN** the author abandons the wizard without confirming
- **THEN** the project's lorebook, documents, and revisions are unchanged
- **AND** only the extraction Job's own audit records exist

#### Scenario: Confirmed candidates become draft Lore entries

- **GIVEN** the author selects a subset of the presented candidates and confirms
- **WHEN** confirmation completes
- **THEN** each selected candidate exists as a `character` or `world` document at `draft` lifecycle status through the existing creation path
- **AND** unselected candidates create nothing
- **AND** each candidate's creation result is reported independently, so a failed creation names its candidate without affecting the others

#### Scenario: Confirmed entries reach prompts only through the existing gate

- **GIVEN** a confirmed wizard-created entry is still `draft`
- **WHEN** a proposal is generated whose corpus matches the entry's keys
- **THEN** the entry contributes nothing, exactly like any other `draft` entry
- **WHEN** the author promotes the entry to `stable` using the existing lifecycle editing
- **THEN** the entry participates in keyword-triggered injection like any other `stable` entry

#### Scenario: Over-budget input fails closed

- **GIVEN** an input segment exceeding the wizard's code-point cap or an assembled extraction prompt exceeding the shared UTF-8 byte authority
- **WHEN** extraction is requested
- **THEN** the request fails before provider construction with a stable capacity error naming the limit
- **AND** no Job provider work, no usage event, and no partial candidate set is produced

#### Scenario: Multi-segment candidates merge deterministically

- **GIVEN** the author extracts two segments that both suggest a character with the same title
- **WHEN** the results are presented
- **THEN** one merged candidate of that kind and title appears, carrying the union of both segments' suggested aliases
- **AND** the candidate list order is deterministic across repeated extractions of the same segments

#### Scenario: Extraction failures stay inside the provider diagnostics boundary

- **GIVEN** the configured provider fails persistently during extraction
- **WHEN** the wizard reports the failure
- **THEN** the failure surfaces through the Studio error surface with the standard error envelope
- **AND** no provider response body is exposed beyond the provider failure diagnostics boundary
- **AND** no Lore entry is created from the failed run
