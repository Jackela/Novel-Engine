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

- The Studio Inspector gains a `lore` tab hosting a project-scoped
  lorebook initialization wizard (URL-backed activation, same tab contract
  as every Inspector surface) that walks the author from existing draft
  material to confirmed Lore entries: provide text (paste, or select
  already-imported chapter documents), run extraction, review candidates,
  confirm.
- Wizard input is a list of segments — one paste or one selected document's
  current content each. Each segment is extracted by its own `lore-extract`
  Job, so every segment keeps its own audit trail, its own keyed-retry and
  replay semantics, and exactly one usage event per completed provider
  request under the existing usage accounting rules.
- Extraction runs as a structured generation request through the configured
  provider (the ai context's structured text generation path — the same
  provider authority, model resolution, retry, and failure boundaries as
  proposal generation). Candidates are suggestions only: each candidate
  carries a document kind (`character` or `world`), a title, suggested
  aliases, and a summary body.
- With the trial (mock) provider the wizard still works end to end: each
  segment produces deterministic placeholder candidates clearly labeled as
  trial output, using the same trial-mode language as the #615 first-run
  explainer (generation on the built-in trial provider; connect a real
  provider for real extraction).
- Nothing persists before the author confirms. Candidates live only in the
  wizard session; until the explicit confirm step, the wizard creates no
  document, no revision, and no Lore lifecycle state, and abandoning the
  wizard leaves the project untouched. The per-segment extraction Jobs are
  ordinary audit records, exactly like every other AI request.
- Cross-segment candidate merging happens client-side over the completed
  segment Jobs: candidates with the same kind and title collapse to one
  candidate carrying the union of suggested aliases, in a deterministic
  order, recomputed from the session's completed segment results.
- Confirmation is per candidate and runs two existing steps in sequence —
  the existing lorebook document creation call, then the existing Lore
  alias write path for that candidate's aliases. The two steps are not
  atomic: if the alias write fails, the entry already exists, and the
  wizard reports that candidate's result honestly as created-with-failed-
  aliases so the author can retry the alias write rather than silently
  losing the aliases. Each candidate's outcome is reported independently.
- Confirmation creates entries at `draft` lifecycle status like any new
  Lore entry. The draft/stable/deprecated state machine, the injection gate
  (only non-empty `stable` entries inject), and Canon semantics are
  untouched — after confirmation the author promotes entries to `stable`
  with the existing document-scoped lifecycle editing, and only then do
  they reach generation prompts.
- Each input segment is capped at 100,000 Unicode code points. A segment
  over the cap fails before provider construction with the stable 422
  `GENERATION_CAPACITY_EXCEEDED` envelope whose details carry
  `resource: lore_extract_segment`, `limit: 100000`, and an `observed`
  value bounded to the limit plus one — the same inline details shape as
  the generation capacity envelopes. Each segment's assembled extraction
  prompt (fixed labels plus that segment's content) is separately capped
  by the shared 8,388,608 UTF-8 byte authority; over-budget prompts fail
  closed the same way. Wizard input is never silently truncated — the
  author splits or trims oversized material.
- Any retrieval the wizard performs over existing project content behaves
  exactly like the product's full-text search: operator-laden input is
  safely reduced to strict tokens, irreducible input returns no results,
  and every query runs as a token-reduced parameterized search — never as
  a free-form match expression.
- Extraction failures surface through the Studio error surface with the
  provider diagnostics boundary intact; a failed or abandoned wizard run
  never produces partial Lore entries.
- The Job model's closed enums extend to carry the new work: JobSummary
  `kind` gains `lore-extract` and `operation` gains `extract`, the
  synchronous execution model's kind list extends to match, and
  `lore-extract` Jobs are retryable under the same retry chain rules as
  proposal, review, and export Jobs (import remains the only non-retryable
  kind).

## Impact

- Spec deltas: one ADDED requirement (Guided lorebook initialization) and
  two MODIFIED requirements — the Synchronous job execution model (kind and
  operation enums plus the synchronous kind list gain the extraction
  entries; its complete-payload sentence extends to lore-extract responses
  so summary and detail stay consistent) and the Job retry chain
  (`lore-extract` joins the retryable kinds and the stored-outcome replay
  set). Existing requirements otherwise constrain the wizard unchanged
  (keyword-triggered lore entries, document-scoped Lore lifecycle editing,
  usage accounting, provider failure boundary).
- Frontend: the `lore` Inspector tab (tab union, route state, Inspector
  panels), the wizard flow, and the client-side segment merge. The tab
  union, `studioRouteState`, and `StudioInspectorPanels` are shared files
  with the writing-stats change's `stats` tab: the two changes serialize on
  those files (stats first, lore second) rather than editing them in
  parallel. Frontend job types extend (`StudioJobKind`,
  `StudioJobSummaryKind`, `StudioJobSummaryOperation`).
- Backend: a studio application extraction service orchestrating the ai
  context port, the `lore-extract` Job type, and its HTTP route; the Job
  enum SSOT extends (`JOB_SUMMARY_KINDS`, `JOB_SUMMARY_OPERATIONS` in
  `payload_schemas/job.ts` and their guards in `payloads.ts`).
- Every completed extraction segment records usage under the existing
  usage accounting rules, so wizard extractions appear in project usage
  totals like any other AI request.
- The OpenAPI baseline regenerates (route-adding change).
- No database migration, no new dependency, no environment variable, no
  change to Lore lifecycle status semantics, injection budgets, progressive
  disclosure ordering, or resident-context assembly.
- Issue linkage: implements #614 (A2-06) from the 2026-09-13 productization
  campaign evidence in `docs/agents/productization-2026-09-13.md`.

## Non-goals

- No change to the `draft`/`stable`/`deprecated` state machine or the
  Canon gate; confirmation creates `draft` entries only, and the wizard
  never auto-promotes to `stable`.
- No atomic cross-candidate or cross-step confirmation transaction: the
  two-step per-candidate path deliberately reports partial success rather
  than rolling back created entries.
- No auto-tracking or incremental re-extraction as the manuscript grows
  (Novelcrafter Codex progression tracking is a separate future
  capability).
- No cross-project template library or lorebook import/export (A2-09
  territory).
- No automatic chunking of a single oversized segment; over-budget
  segments are rejected with guidance to split the input.
