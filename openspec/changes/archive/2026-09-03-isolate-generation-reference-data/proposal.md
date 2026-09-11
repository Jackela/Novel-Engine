# Isolate generation reference data from prompt instructions

## Why

Proposal prompts delimit the author instruction and target manuscript as
untrusted data, but insert the project outline, linked beat, prior-story
digests, recent text, and Lore titles/bodies directly into the user prompt.
Those fields can contain imported or AI-accepted text. A stored value can
therefore reproduce a section closer such as `[END LOREBOOK]` and place an
instruction-looking line outside the apparent data block. Lore lifecycle
approval decides canon eligibility; it does not grant prompt-instruction
authority.

## What Changes

- Declare every project-derived generation context section to be reference
  data that cannot override the system or author instruction.
- Encode every dynamic string in outline, linked-beat, prior-story,
  recent-text, Lore, and author-instruction sections with one collision-free,
  reversible prompt-data codec inside assembler-owned delimiters.
- Encode reserved square brackets and the codec escape character so stored
  content cannot create a second structural opener or closer and a reference
  decoder can recover the exact original text.
- Keep author instructions in their existing dedicated block and keep the
  target manuscript in its existing untrusted JSON block.
- Route synchronous, streaming, keyed-retry, and whole-book generation through
  the same prompt assembly and system instruction.

## Impact

- Provider prompts become structurally explicit about instruction authority.
  Stored prose remains recoverable byte-for-byte through the prompt-data codec,
  but it cannot render an assembler-owned delimiter.
- No route, payload, database, migration, dependency, or Lore lifecycle change
  is required.
- Existing deterministic prompt fixtures change deliberately and must be
  regenerated through source edits, not snapshot acceptance without review.

## Non-goals

- No generation-context size limit or Lore planner optimization; those are
  separate resource-capacity work.
- No change to which Lore entries match, their promotion order, or lifecycle
  eligibility.
- No attempt to claim that prompt formatting alone makes an LLM immune to
  prompt injection; this change establishes the application's authority and
  structural-boundary contract.
- No revision-snapshot or retry-base semantic change.

## Validation

- Hostile author instruction, outline, beat, prior-story, recent-text, Lore
  title/summary/body, and manuscript fixtures containing every reserved
  opener/closer, literal codec escape sequence, and instruction-like prose.
- Marker-count and codec round-trip assertions proving only assembler
  structure appears and stored text remains data.
- Synchronous, streaming, retry, and whole-book prompt-capture regressions plus
  server type, lint, architecture, size, full tests, and strict OpenSpec.
