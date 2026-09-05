# Lorebook

The lorebook is the keyword-triggered **layer 2** of the two-layer generation context (ADR-0004). There is no separate lore storage: every **character** or **world** document *is* a **Lore entry**. Its keys are the trimmed document title plus its declared aliases, and its content is the document's current revision Markdown. Lifecycle status is the closed set `draft | stable | deprecated`: new entries start as `draft`, migrated entries remain `stable`, and only non-empty matching `stable` entries may join a generation prompt.

**Primary sources:** `CONTEXT.md`, `docs/adr/0004-two-layer-generation-context.md`, `docs/adr/0006-lore-lifecycle-gating.md`, `server/src/contexts/studio/application/lorebook.ts`.

## Keyword triggering

Selection lives in `matchLoreEntries` (`server/src/contexts/studio/application/lorebook.ts`):

- **Keys** — `loreEntryKeys` combines the trimmed title with the parsed alias list. Stored aliases live in the document's `loreAliasesJson` column (`server/src/contexts/studio/infrastructure/db/schema.ts`) and are parsed defensively: anything but a string array reads as no aliases, so a malformed stored value can never break prompt assembly.
- **Matching is case-insensitive substring occurrence** over the combined corpus (resident corpus + manuscript). Whole-token boundaries are deliberately *not* required, so a name embedded in a larger word still triggers. This is a documented #315 contract, not an oversight.
- **Empty entries never render** — an entry whose current revision has no injectable markdown text is skipped even when its keys hit.
- **Lifecycle fails closed** — `draft` and `deprecated` entries are omitted before key matching. An unreadable stored status behaves as `draft`; write paths accept only the closed set.
- **Order is deterministic** — `loreEntriesFromDocuments` filters the character/world entries from `ProposalContextSource.documents` without sorting them again. Equal-rank matches therefore retain the canonical composite order captured once by the Store.

The resident side of the corpus is the **raw** view text (`residentMatchCorpus` in `server/src/contexts/studio/application/resident_context.ts`), not the sanitized render, so keyword hits stay identical regardless of render-time sanitization.

Lore content, aliases, lifecycle status, the outline, linked beat, prior chapters, and target revision all come from the same short `readProposalContext` SQLite snapshot. Prompt assembly derives Lore inputs purely from that captured value; it does not call the legacy per-document, per-volume, or per-Lore Store reads.

## Relationship to character and world documents

Because entries are documents, not copies, they inherit document semantics:

- Editing a character/world document updates the entry immediately; no resync step exists.
- Only the two lorebook kinds (`LOREBOOK_ENTRY_KINDS`) participate. Writes to other kinds' aliases answer 422; reads of non-lore kinds default to an empty list.
- Alias normalization is a **write-path contract** (`normalizeLoreAliases`): trim every alias, drop blanks and entries over 240 characters, dedupe case-insensitively keeping the first spelling, and cap the list at `MAX_LORE_ALIASES` (64). Readers always see trimmed, deduped aliases.

**Primary sources:** `server/src/contexts/studio/application/lorebook.ts`, `server/src/contexts/studio/application/lore_alias_service.ts`.

## Injection point

`buildProposalUserPrompt` composes the whole user prompt: operation and author instruction, the rendered resident sections, then the triggered lorebook sections, and finally the target manuscript inside the untrusted block (see `resident-context.md` for the layer-1 detail). Matched entries render under one `[BEGIN LOREBOOK]` / `[END LOREBOOK]` marker pair, while Lore titles, summaries, and full text are encoded so source text cannot forge a server delimiter (`server/src/contexts/studio/application/sanitization.ts`).

Progressive disclosure starts every match as a visibly marked summary, then promotes full Markdown while the rendered Lore section fits the configured character budget. Title hits are considered before alias hits; ties retain document reading order. A match that cannot expand remains visible as a summary and is never silently dropped. The default full-text promotion budget is 4000 characters; `LLM_LOREBOOK_BUDGET_CHARACTERS` supplies a validated positive override.

Synchronous, SSE streaming, and retry generation all pass the same captured `ProposalContextSource` to `buildProposalTask`. Lore projection, matching, promotion, prompt-data encoding, and incremental complete-prompt admission therefore share one implementation (`server/src/contexts/studio/application/proposal_landing.ts`, `proposal_streaming.ts`, `job_retry_executor.ts`). The Lore promotion budget remains separate from the complete system-plus-user prompt limit of 8 MiB; a prompt over that limit is refused before Provider construction.

## API surface

Entry content remains managed through the ordinary document routes (`server/src/contexts/studio/interface/http/document_routes.ts`). Lore-specific routes own aliases and lifecycle status:

| Method | Path | Behavior |
|---|---|---|
| `GET` | `/api/projects/:projectId/documents/:documentId/aliases` | Read the normalized alias list; non-lore kinds answer an empty list |
| `PUT` | `/api/projects/:projectId/documents/:documentId/aliases` | Replace the alias list wholesale; normalization applies; no revision is minted and content stays untouched; non-lore kinds answer 422 |
| `PUT` | `/api/projects/:projectId/documents/:documentId/lore-status` | Replace lifecycle status with one closed-set value; no revision is minted; non-lore kinds or invalid values answer 422 |

The routes are thin handlers over Lore application services behind the principal guard (`server/src/contexts/studio/interface/http/lore_routes.ts`, schemas in `lore_schemas.ts`). The Studio consumes the generated HTTP union through one exhaustive runtime definition in `frontend/src/app/loreStatus.ts`.
