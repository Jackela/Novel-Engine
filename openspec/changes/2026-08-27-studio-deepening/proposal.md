# Studio deepening: context assembly, volume hierarchy, LLM review, simplifications

## What

Six adjudicated slices from the 2026-08-27 grilling session (competitor-informed
audit vs the popular open-source AI-novel projects):

1. **Guest removal (simplification)** — the guest principal, its session
   surface, sandbox cleanup, and entry flow are removed; the product is
   single-owner end to end.
2. **Volume hierarchy** — chapters group into volumes (fixed two-level:
   project → volume → chapter), with a chapter ↔ outline-beat association so
   structure drives generation.
3. **Two-layer generation context** — proposals assemble a resident context
   (outline position, rolling summary of prior chapters, recent-chapter tail)
   plus keyword-triggered lore entries derived from character/world documents
   (SillyTavern-style lorebook; keys = title + declared aliases).
4. **LLM editorial review** — the review runs the existing
   `editorial_review` provider step over the snapshot and reports findings in
   a closed dimension set with blocker/warning severities, replacing the
   word-count checks.
5. **Project usage surface** — a simple project-scoped aggregation over the
   already-recorded usage events.
6. **Whole-book generation loop** — a frontend-driven, stoppable, resumable
   chapter-by-chapter auto-accept loop over the existing synchronous
   proposal/accept endpoints (the advanced auto pipeline; a background
   long-task variant is deliberately deferred).

## Why

The audit found the backend's generation pipeline amnesiac (prompts carried
only the target chapter), the outline/character/world documents dead weight
(no pipeline consumed them), review a word counter wearing an
`editorial_review` name, and accumulated simplification debt (guest surface,
unconsumed usage accounting). The popular projects all converge on context
assembly + structure-driven generation as the core of long-form AI writing;
this change brings the contract up to that bar while cutting what the
single-owner product does not need.

## Impact

- Extends the `novel-engine` capability: seven ADDED requirements, eight
  MODIFIED (guest references retired), one REMOVED
  (`Principal-scoped data isolation` superseded by `Owner data isolation`).
- Schema: volumes table + chapter volume/beat links (drizzle migration);
  guest columns become unused and are dropped in the same migration series.
- Two ADRs record the irreversible calls: two-layer context assembly
  (ADR-0004) and the fixed two-level hierarchy (ADR-0005).
- Knowledge glossary (CONTEXT.md) already carries the new terms: Lore entry,
  Resident context, Volume, Beat, Review dimension; Guest removed.
- Streaming output stays deferred (#308) and depends on slice 3.
