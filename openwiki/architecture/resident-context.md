# Resident context

Every proposal generation assembles a **two-layer context** ahead of the target manuscript (ADR-0004). Layer 1 is the **resident context** — always injected, deterministic, never model-generated. Layer 2 is the keyword-triggered **lorebook** of character and world entries (see `CONTEXT.md` for both terms). This page covers layer 1; the lorebook trigger mechanism has its own page (`lorebook.md`) and lives in `server/src/contexts/studio/application/lorebook.ts`.

**Primary sources:** `docs/adr/0004-two-layer-generation-context.md`, `server/src/contexts/studio/application/resident_context.ts`.

## What the resident view holds

`assembleResidentContext` is a pure function over documents, the target document ID, and the resolved beat link. Its view has three parts:

- **Outline** — the full markdown of the project's first outline-kind document, plus the target chapter's linked beat resolved against the live outline. A project without an outline contributes no outline section.
- **Prior story** — a rolling summary of *every* chapter strictly before the target in reading order; no chapter is elided. Each entry is a deterministic digest: the chapter's flattened opening prose truncated to `PRIOR_STORY_DIGEST_WORD_LIMIT` (60 words), or the `(no text yet)` placeholder for empty chapters.
- **Recent text** — the closing passage of the most recent earlier chapter with text, up to `RECENT_TEXT_CHARACTER_LIMIT` (1200 characters), cut at a line or space boundary inside a snap window so the tail starts at a word edge.

The reading order is volume rank first, then in-volume position, with the document ID as a deterministic tie-break; chapters whose volume no longer resolves sort last (`compareChapters` in `resident_context.ts`). The recent-text tail always comes from text *other* than the target's own manuscript: when drafting the next chapter that is the previous chapter's ending, and when continuing a chapter the target's full text already rides verbatim in the untrusted manuscript block.

**Primary sources:** `server/src/contexts/studio/application/resident_context.ts`, `server/src/contexts/studio/application/beat_association_service.ts`.

## From view to prompt

`buildProposalUserPrompt` composes the whole user prompt: the operation and author instruction, the rendered resident sections, the triggered lorebook sections, and finally the target manuscript inside the `[BEGIN UNTRUSTED MANUSCRIPT JSON]` block. Rendering routes every derived prose line through `sanitizeResidentProse` so summaries and tails can neither inject instructions nor forge a bracketed marker; the outline itself stays writer-trusted (`server/src/contexts/studio/application/sanitization.ts`).

Lore entries are matched over the **raw** resident view text (`residentMatchCorpus`), so keyword hits stay identical regardless of render-time sanitization. Because the assembler is pure, its coverage is pinned by unit tests rather than provider behavior; the SSE streaming pipeline builds its provider task through the same assembly, so streamed and synchronous prompts match (`server/src/contexts/studio/application/proposal_streaming.ts`).

**Primary sources:** `server/src/contexts/studio/application/resident_context.ts`, `server/src/contexts/studio/application/sanitization.ts`, `server/src/contexts/studio/application/lorebook.ts`, `server/src/contexts/studio/application/proposal_landing.ts`, `server/src/contexts/studio/application/proposal_streaming.ts`.
