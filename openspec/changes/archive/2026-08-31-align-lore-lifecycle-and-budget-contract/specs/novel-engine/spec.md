## MODIFIED Requirements

### Requirement: Keyword-triggered lore entries
Character and world documents MUST serve as Lore entries whose keys are the
trimmed document title plus normalized aliases. Lore lifecycle status MUST be
the closed set `draft`, `stable`, and `deprecated`; new entries MUST default
to `draft`, while entries created before lifecycle migration MUST remain
`stable`. Only a non-empty `stable` entry whose key occurs in the resident
context or target manuscript MAY enter a generation prompt. Matching `draft`
and `deprecated` entries MUST be omitted completely.

Every eligible match MUST first be represented by a visibly marked summary.
The system MUST then promote entries to full current Markdown within a
configurable character budget, prioritizing title hits before alias hits and
preserving reading order for ties. A match that cannot be promoted MUST remain
visible as its summary rather than being silently dropped. The default budget
MUST be 4000 characters, and a valid positive environment override MUST apply
to synchronous, streaming, retry, and whole-book generation through the same
Lore assembly.

#### Scenario: Draft and deprecated hits are omitted
- **GIVEN** matching character or world entries are `draft` or `deprecated`
- **WHEN** a proposal is generated
- **THEN** neither entry contributes content or a summary to the prompt

#### Scenario: Alias triggers injection
- **GIVEN** a non-empty `stable` Lore entry whose alias occurs in the generation corpus
- **AND** its full rendering fits within the configured budget
- **WHEN** a proposal is generated
- **THEN** the entry's current Markdown is injected into the prompt

#### Scenario: Over-budget matches remain visible
- **GIVEN** multiple matching `stable` entries cannot all expand within the configured budget
- **WHEN** a proposal is generated
- **THEN** every match appears as a visibly marked summary
- **AND** only entries that fit are promoted to full Markdown

#### Scenario: Promotion order is deterministic
- **GIVEN** matching stable entries include both title and alias hits
- **WHEN** the budget permits only some full-text promotions
- **THEN** title hits are considered before alias hits
- **AND** equal-rank entries retain project reading order

#### Scenario: No key hit, no injection
- **GIVEN** no stable Lore key occurs in the resident context or target manuscript
- **WHEN** a proposal is generated
- **THEN** the prompt contains no Lore section

#### Scenario: Existing Lore remains stable after migration
- **GIVEN** a Lore entry predates the lifecycle migration
- **WHEN** the migration completes
- **THEN** the entry is `stable` and remains eligible for matching

#### Scenario: Every generation path shares Lore assembly
- **GIVEN** the same project revisions, generation corpus, and Lore budget
- **WHEN** generation runs synchronously, by stream, by retry, or as part of a whole-book run
- **THEN** each path applies the same lifecycle gate, matching, summaries, and promotion order
