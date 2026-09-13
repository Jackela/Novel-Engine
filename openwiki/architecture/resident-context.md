# Resident context

Every proposal generation assembles a **two-layer context** ahead of the target manuscript (ADR-0004). Layer 1 is the **resident context** — always injected, deterministic, never model-generated. Layer 2 is the keyword-triggered **lorebook** of character and world entries (see `CONTEXT.md` for both terms). This page covers layer 1; the lorebook trigger mechanism has its own page (`lorebook.md`) and lives in `server/src/contexts/studio/application/lorebook.ts`.

**Primary sources:** `docs/adr/0004-two-layer-generation-context.md`, `server/src/contexts/studio/application/ports/proposal_context_store.ts`, `server/src/contexts/studio/infrastructure/proposal_context_store_part.ts`, `server/src/contexts/studio/application/resident_context.ts`.

## One coherent source snapshot

Before prompt assembly, `readProposalContext` captures the scoped target and its current revision, every project document paired with its current revision, and the ordered volumes inside one short SQLite read transaction. The returned `ProposalContextSource` is a plain immutable application value; the transaction closes before prompt rendering, Provider construction, network work, or streaming delivery.

`documentsWithCurrent` establishes the project's canonical composite document order once at this capture boundary. Resident and Lore derivation preserve that captured order and perform no second sort or individual Store read, so target text, outline, beat reference, prior chapters, and Lore state all describe the same database snapshot.

## What the resident view holds

`residentContextSourceFromProposalContext` derives the outline and linked beat purely from the captured documents and target beat reference. `assembleResidentContext` then remains a pure function over that projection. Its view has three parts:

- **Outline** — the full markdown of the project's first outline-kind document, plus the target chapter's linked beat resolved against the live outline. A project without an outline contributes no outline section.
- **Prior story** — a rolling summary of *every* chapter strictly before the target in reading order; no chapter is elided. Each entry is a deterministic digest: the chapter's flattened opening prose truncated to `PRIOR_STORY_DIGEST_WORD_LIMIT` (60 words), or the `(no text yet)` placeholder for empty chapters.
- **Recent text** — the closing passage of the most recent earlier chapter with text, up to `RECENT_TEXT_CHARACTER_LIMIT` (1200 characters), cut at a line or space boundary inside a snap window so the tail starts at a word edge.

Chapter order is the chapter subsequence of the canonical composite order already captured by the Store; `assembleResidentContext` does not recalculate or compete with its volume, position, creation-time, and ID tie-breaks. The recent-text tail always comes from text *other* than the target's own manuscript: when drafting the next chapter that is the previous chapter's ending, and when continuing a chapter the target's full text already rides verbatim in the untrusted manuscript block.

**Primary sources:** `server/src/contexts/studio/infrastructure/db/studio_query_helpers.ts`, `server/src/contexts/studio/application/resident_context.ts`, `server/src/contexts/studio/application/outline_beats.ts`.

## From view to prompt

`buildProposalUserPrompt` composes the whole user prompt: the operation and author instruction, the rendered resident sections, the triggered lorebook sections, and finally the target manuscript inside the `[BEGIN UNTRUSTED MANUSCRIPT JSON]` block. Rendering routes project-derived prose, including the outline and linked beat, through `sanitizeResidentProse` so source text cannot forge a server delimiter. The system prompt declares every resident, Lore, and manuscript block to be reference data rather than instructions (`server/src/contexts/studio/application/sanitization.ts`, `proposal_landing.ts`).

Lore entries are matched over the **raw** resident view text (`residentMatchCorpus`), so keyword hits stay identical regardless of render-time encoding. `BoundedPromptWriter` admits each line incrementally and enforces the complete system-plus-user prompt limit of 8 MiB before Provider construction. Synchronous, SSE streaming, and retry generation all build their task through this same captured-context assembly (`server/src/contexts/studio/application/proposal_service.ts`, `proposal_streaming.ts`, `job_retry_executor.ts`).

**Primary sources:** `server/src/contexts/studio/application/resident_context.ts`, `server/src/contexts/studio/application/sanitization.ts`, `server/src/contexts/studio/application/generation_capacity.ts`, `server/src/contexts/studio/application/proposal_landing.ts`, `server/src/contexts/studio/application/proposal_streaming.ts`.
