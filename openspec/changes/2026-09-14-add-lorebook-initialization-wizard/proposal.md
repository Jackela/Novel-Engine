# Guided lorebook initialization wizard

## Why

A project's two-layer generation context (ADR-0004) only works when the
lorebook has entries: keyword-triggered Lore injection matches nothing in an
empty lorebook, so every fresh project generates with resident context alone
and an author who already has a draft gets no continuity benefit. Seeding
that lorebook today is entirely manual — create `character` and `world`
documents one by one, write aliases by hand, promote lifecycle status by
hand. The 2026-09-13 productization campaign scored this as the biggest
product-level onboarding gap (competitor matrix A2-06, P1: Sudowrite's Story
Bible and Novelcrafter's Codex both own the "feed your draft, get a story
bible" pattern) and parked it as #614 with explicit ready-state requirements:
an OpenSpec change, reuse of the resident-context pipeline, FTS5
parameterization red lines, and a multi-ticket epic. This change is that
proposal.

## What Changes

- The Studio gains a project-scoped lorebook initialization wizard that
  walks the author from existing draft material to confirmed Lore entries:
  provide text (paste, or select already-imported chapter documents), run
  extraction, review candidates, confirm.
- Extraction runs as a structured generation request through the configured
  provider (the ai context's structured text generation path — the same
  provider authority, model resolution, retry, and failure boundaries as
  proposal generation). Candidates are suggestions only: each candidate
  carries a document kind (`character` or `world`), a title, suggested
  aliases, and a summary body.
- With the trial (mock) provider the wizard still works end to end: it
  produces deterministic placeholder candidates clearly labeled as trial
  output, using the same trial-mode language as the #615 first-run explainer
  (generation on the built-in trial provider; connect a real provider for
  real extraction).
- Nothing persists before the author confirms. Until the explicit confirm
  step, the wizard creates no document, no revision, and no Lore lifecycle
  state; abandoning the wizard leaves the project untouched. The extraction
  Job itself is ordinary audit records, exactly like every other AI request.
- Confirmation creates entries through the existing lorebook document
  creation path, one candidate at a time, each starting at `draft`
  lifecycle status like any new Lore entry. The draft/stable/deprecated
  state machine, the injection gate (only non-empty `stable` entries
  inject), and Canon semantics are untouched — after confirmation the author
  promotes entries to `stable` with the existing document-scoped lifecycle
  editing, and only then do they reach generation prompts.
- Wizard input is bounded by an explicit budget aligned with the generation
  context capacity discipline: pasted text and selected-document content are
  capped in Unicode code points, the assembled extraction prompt is capped
  in UTF-8 bytes under the same 8,388,608-byte authority as proposal
  generation, and over-budget input fails closed with a stable capacity
  error — never silently truncated.
- Long material is handled by multi-segment input, not silent truncation:
  the author may add several text segments (or several documents) to one
  wizard session, each segment is extracted independently within its own
  budget, and candidates from all segments merge into one deduplicated list
  (same kind + same title collapse to one candidate).
- Any retrieval the wizard performs over existing project content goes
  through the strict-token reduction (`buildFtsMatchQuery`) and
  parameterized FTS5 MATCH — the wizard adds no SQL or FTS5 expression
  built by string concatenation.
- Extraction failures surface through the Studio error surface with the
  provider diagnostics boundary intact (no provider body leaks); a failed or
  abandoned wizard run never produces partial Lore entries.

## Decisions

These constraints bind the implementation tickets:

- **Structured generation via the configured provider.** Extraction reuses
  the ai context's structured text generation pipeline and its ports;
  the mock provider yields placeholder candidates plus trial-mode labeling
  consistent with #615. No separate extraction model path, no client-side
  extraction heuristics.
- **Zero content persistence before confirmation.** Candidates live only in
  the wizard session (and the extraction Job's own audit payload); they are
  never draft documents. Confirmation replays through the existing lorebook
  creation service and its gates.
- **FTS5 red line.** Wizard-side search over existing documents must go
  through `buildFtsMatchQuery` and parameterized MATCH; the extraction
  pipeline adds no SQL string concatenation anywhere.
- **Input budget mirrors proposal generation.** Per-segment code-point caps
  and the shared UTF-8 prompt-byte authority, fail-closed on breach (the
  `bound-generation-context-capacity` precedent); multi-segment merge with
  deterministic deduplication instead of auto-chunking a single oversized
  paste.

## Impact

- Frontend: new wizard surface with an Inspector entry point (empty-lorebook
  guidance plus a persistent entry in the Lore area), candidate review list,
  per-candidate confirm results. Backend: a studio application extraction
  service orchestrating the ai context port, one new Job type for the
  extraction request, and its HTTP route; confirmation reuses existing
  document creation with no new batch semantics.
- New AI requests record usage under the existing usage accounting rules, so
  wizard extractions appear in project usage totals like any other AI
  request.
- The OpenAPI baseline regenerates (route-adding change).
- No database migration, no new dependency, no environment variable, no
  change to Lore lifecycle status semantics, injection budgets, progressive
  disclosure ordering, or resident-context assembly.
- Spec: one added requirement (Guided lorebook initialization) in the
  `novel-engine` capability; existing requirements constrain the wizard
  unchanged (keyword-triggered lore entries, document-scoped Lore lifecycle
  editing, usage accounting, provider failure boundary).
- Issue linkage: implements #614 (A2-06) from the 2026-09-13 productization
  campaign evidence in `docs/agents/productization-2026-09-13.md`.

## Non-goals

- No change to the `draft`/`stable`/`deprecated` state machine or the
  Canon gate; confirmation creates `draft` entries only, and the wizard
  never auto-promotes to `stable`.
- No auto-tracking or incremental re-extraction as the manuscript grows
  (Novelcrafter Codex progression tracking is a separate future capability).
- No cross-project template library or lorebook import/export (A2-09
  territory).
- No automatic chunking of a single oversized paste; over-budget segments
  are rejected with guidance to split the input.
