## ADDED Requirements

### Requirement: Generation reference-data authority

The proposal system prompt MUST be the sole system-instruction authority. The
author-instruction block MAY request story behavior but MUST be identified as
untrusted user instruction that cannot replace system policy. Project outline,
linked beat, prior-story digests, recent chapter text, Lore titles and bodies,
and the target manuscript MUST be identified as reference data without system,
developer, or user instruction authority. Lore lifecycle approval MUST affect
eligibility only and MUST NOT grant instruction authority.

Every dynamic string inside a generation section MUST pass through one
collision-free, reversible prompt-data encoding before interpolation. The
encoding MUST cover its own escape character and reserved square brackets so a
stored value cannot create an additional structural opener or closer and a
reference decoder can recover the original value without silent deletion or
rewriting. The system prompt MUST declare the exact escape decoding rules so
encoded backslashes and Markdown retain their source meaning. Synchronous,
streaming, keyed-retry, and whole-book generation MUST share this authority and
encoding contract.

#### Scenario: Stored Lore cannot close its data section

- **GIVEN** a matching stable Lore entry whose title or body contains a Lore
  closer followed by instruction-looking prose
- **WHEN** a proposal prompt is assembled
- **THEN** the assembler emits exactly one Lore opener and one Lore closer
- **AND** the stored closer and prose remain encoded inside the Lore data block
- **AND** reference decoding recovers the original title or body

#### Scenario: Outline and beat remain reference data

- **GIVEN** an outline or linked beat contains reserved prompt markers and a
  request to ignore earlier instructions
- **WHEN** any proposal pipeline assembles its provider task
- **THEN** those values appear only as encoded reference data
- **AND** the system prompt denies the block instruction authority

#### Scenario: Every proposal path shares the boundary

- **GIVEN** the same project revisions and proposal request
- **WHEN** generation runs synchronously, by stream, by keyed retry, or through
  the whole-book loop
- **THEN** each provider task applies the same reference-data delimiters,
  encoding, and system authority statement

## MODIFIED Requirements

### Requirement: Resident context injection

Every proposal generation MUST assemble the resident context ahead of the
target manuscript: the outline with its current beat position, a rolling
summary of the prior chapters, and the tail of the most recent chapter. The
assembly MUST draw only from the project's own documents, and the rolling
summary MUST cover every prior chapter in reading order. Outline, beat,
prior-story, and recent-text values MUST be encoded inside their reference-data
blocks under the generation reference-data authority Requirement.

#### Scenario: Continuation sees the prior story

- **GIVEN** a project with an outline and three completed chapters
- **WHEN** a proposal is drafted for the next chapter
- **THEN** the provider prompt contains encoded outline data, a summary
  covering chapters 1 through 3, and the tail of chapter 3
- **AND** the target chapter's manuscript follows the resident context
