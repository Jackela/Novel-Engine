# Design: guided lorebook initialization wizard

## Context

The wizard is the first product surface that turns existing draft material
into Lore entries. It touches three established pipelines: the ai context's
structured text generation (provider authority, model resolution, retry),
the Job execution model (durable, evented, retryable, usage-accounted), and
the lorebook document lifecycle (ADR-0006 gating). The design goal is to add
one guided flow without inventing new persistence or new atomicity
contracts.

## Option 1: extraction as a synchronous request — rejected

A plain POST that calls the provider and returns candidates in one response
would be the smallest surface, but it bypasses the Job execution model every
other AI request obeys: no events, no retry chain, no usage accounting
trail, and a long extraction inside one request contradicts the synchronous
execution discipline that jobs exist to audit.

**Chosen instead — Option 2: extraction as Jobs, one per segment.** Each
input segment (one paste or one selected document) runs as its own
`lore-extract` Job that executes synchronously inside its request like
proposal generation, records its events, participates in keyed retry with
stored outcomes, and records exactly one usage event per completed provider
request. One job per segment — rather than one job per wizard session —
keeps usage singularity and replay keyed to exactly one provider request,
which a multi-segment aggregate job would blur. The candidate set of each
segment rides that segment's terminal Job payload.

The Job model's closed enums extend to admit the new kind and operation
(`lore-extract` / `extract`) through the same SSOT constants every other
kind flows through; `lore-extract` inherits retryability from the same
retry chain rules as proposal, review, and export.

## Option 3: candidates as draft documents — rejected

Persisting candidates immediately as `draft` Lore entries would make
confirmation a promotion, but it violates the product constraint that the
author confirms before anything lands: an abandoned wizard would litter the
navigator with half-real entries, and "zero content persistence before
confirmation" is the trust posture #614 asks for. Candidates live only in
the wizard session, assembled client-side from the completed segment Jobs;
the Job payloads are audit state, not product content.

## Cross-segment merge: client-side, deterministic

Segments extract independently, so merging belongs where the session lives:
the client folds the completed segment Jobs' candidate sets into one list,
collapsing same-kind, same-title candidates to one entry carrying the union
of suggested aliases, ordered deterministically (kind, then title, then
first-segment occurrence). Re-running the merge over the same completed
segments yields the same list. The server stays single-segment and
stateless about wizard sessions.

## Confirmation path: two existing steps per candidate, deliberately non-atomic

Each selected candidate runs the existing lorebook document creation call,
then the existing Lore alias write path for its aliases. A batch endpoint
or a cross-step transaction would create a new atomicity contract no
existing surface needs; instead the wizard reports each candidate's outcome
honestly in three states — created, created-with-failed-aliases (entry
exists, alias write failed, retryable), and failed (nothing created). A
failed alias write never silently drops the aliases: the candidate keeps
them and the author can retry the write. Partial success is the explicit
semantic, matching how the rest of the Studio surfaces per-item results.

## Input budget: per-segment cap, per-segment prompt authority

The generation context capacity change fixed the discipline: fixed caps,
fail-closed stable errors, never silent truncation. The wizard applies the
same shape at its own boundary:

- Each segment is capped at 100,000 Unicode code points. The figure covers
  a full-length chapter draft (roughly 50k–80k Chinese characters or
  ~60k English words) with headroom, while staying far below any prompt
  concern and cheap to validate before provider construction. A segment
  over the cap is rejected before provider construction with the stable
  422 `GENERATION_CAPACITY_EXCEEDED` envelope, details carrying
  `resource: lore_extract_segment`, `limit: 100000`, and `observed`
  bounded to the limit plus one — the same inline shape as the existing
  generation capacity envelopes.
- Each segment's assembled extraction prompt (fixed labels plus that
  segment's content) counts separately against the shared 8,388,608 UTF-8
  byte authority as proposal generation; a prompt over the authority fails
  closed the same way.
- Oversized material is the author's call: split into more segments or
  trim. No auto-chunking — a silently chunked mega-paste would produce
  candidates the author cannot map back to their material.

## Retrieval over existing content

The wizard's "select existing documents" path lists documents by kind and
reads current content through existing read services; it performs no
free-text search of its own. Any retrieval added later (for example
"does this character already exist?") must behave like the product's
full-text search surface: operator-laden input safely reduced to strict
tokens, irreducible input returning no results, every query running as a
token-reduced parameterized search — which is how the existing FTS
requirement already constrains observable behavior.

## Trial provider behavior

The mock provider is production-legal and is the default first-run
experience (#615). The wizard therefore must work on it: the mock path
returns deterministic placeholder candidates (fixed titles/bodies marked as
placeholders) per segment, and the UI labels the session with the same
trial-mode wording as the entry-page explainer. This keeps the onboarding
loop whole ("paste → see candidates → confirm") with zero configuration,
while the provider-failure boundary still guards misconfigured real
providers.

## Frontend placement

The wizard lives in a new `lore` Inspector tab — the same tab contract
(role=tablist, URL-backed activation, keyboard navigation) as the existing
surfaces, and structurally the same addition as the writing-stats change's
`stats` tab. The tab union, route state, and Inspector panels are shared
files between the two changes; they serialize (stats first, lore second)
rather than editing in parallel. Within the tab, the empty-lorebook state
surfaces the wizard as the primary action — the onboarding moment — and a
persistent entry supports re-extraction once entries exist.
