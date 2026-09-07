## ADDED Requirements

### Requirement: Bounded generation prompt capacity

Every proposal task MUST contain at most 8,388,608 UTF-8 bytes across its
complete system and user prompts, including fixed labels, separators, and
delimiters. Assembly MUST stop at the first fragment that would cross the
limit, MUST NOT retain an oversized joined prompt, and MUST finish before a
Provider is constructed or a streaming response begins.

Capacity refusal MUST return HTTP 422 with code
`GENERATION_CAPACITY_EXCEEDED`, message `Generation capacity exceeded.`, and
details containing only resource `prompt_bytes`, limit, and a safe observed
value saturated at `limit + 1`. Fresh synchronous or streaming refusal MUST
leave no Job, event, usage, proposal, or revision evidence.

A keyed retry's first capacity refusal MUST persist exactly one failed retry
Job and failed event with a closed structured capacity outcome. Replaying the
same key MUST return byte-identical 422 evidence without reassembling context,
constructing a Provider, or creating another row or event. A different key
MUST be a distinct attempt.

#### Scenario: Exact prompt capacity is accepted

- **GIVEN** the complete system and user prompts render to exactly 8,388,608
  UTF-8 bytes
- **WHEN** a proposal task is admitted
- **THEN** the task may be passed to the selected Provider
- **AND** no prompt content is truncated or rewritten to fit

#### Scenario: Plus one refuses before Provider work

- **GIVEN** the complete prompt would render to 8,388,609 UTF-8 bytes
- **WHEN** synchronous or streaming generation is requested
- **THEN** the API returns the stable generation-capacity 422 envelope
- **AND** no Provider is constructed and no durable workflow evidence exists

#### Scenario: Keyed capacity replay is stable

- **GIVEN** a keyed retry has failed permanently on prompt capacity
- **WHEN** the same retry key is submitted again
- **THEN** the API returns byte-identical capacity evidence
- **AND** context assembly, Provider construction, Jobs, and events do not
  repeat

#### Scenario: Whole-book refusal stops later chapters

- **GIVEN** whole-book generation has accepted earlier chapters
- **WHEN** the next chapter exceeds generation prompt capacity
- **THEN** the earlier accepted revisions remain authoritative
- **AND** that chapter and every later chapter remain unaccepted
- **AND** resumption starts from the first still-unaccepted chapter

### Requirement: Bounded prior-story digests

Each non-empty prior chapter digest MUST contain at most 60
whitespace-delimited words and at most 512 Unicode code points, truncating once
with an ellipsis when either limit is crossed. Every prior chapter MUST still
contribute one ordered digest or the existing empty placeholder. The complete
task MUST satisfy the bounded generation prompt capacity Requirement.

#### Scenario: Continuation sees bounded prior story

- **GIVEN** a project with an outline and three completed prior chapters,
  including a chapter whose prose has no spaces
- **WHEN** a proposal is drafted for the next chapter
- **THEN** the provider prompt contains one ordered digest for each of the three
  chapters and the tail of chapter 3
- **AND** no digest exceeds 60 words or 512 Unicode code points

### Requirement: Linear bounded Lore planning

Lore planning MUST compute each matched summary and full representation at
most once, use incremental promotion lengths, and render the final section
once. Existing lifecycle, matching, summary-floor, budget, and promotion-order
semantics MUST remain unchanged. If the all-summary floor makes the complete
prompt exceed bounded generation capacity, generation MUST fail rather than
omit a matched entry.

#### Scenario: Promotion work is linear in rendered input

- **GIVEN** M matched stable Lore entries in deterministic reading order
- **WHEN** their injection plan is assembled
- **THEN** each summary and full representation is computed at most once
- **AND** the planner does not copy or render an M-entry candidate for each
  promotion

#### Scenario: Summary floor never truncates canon

- **GIVEN** all matched summaries exceed the Lore promotion budget
- **WHEN** the complete generation prompt still fits its hard capacity
- **THEN** every match remains visible as a summary
- **WHEN** that summary floor crosses the hard prompt capacity
- **THEN** generation fails without silently dropping any matched entry
