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

**Chosen instead — Option 2: extraction as a Job.** One new Job type
(`lore-extract`) runs synchronously inside the request like proposal
generation, records its events, participates in keyed retry with stored
outcomes, and records exactly one usage event per completed provider
request. The candidate set rides the terminal Job payload; the wizard reads
it from the Job result. This reuses every existing guarantee (idempotent
replay, usage singularity, failure boundaries) instead of paralleling them.

## Option 3: candidates as draft documents — rejected

Persisting candidates immediately as `draft` Lore entries would make
confirmation a promotion, but it violates the product constraint that the
author confirms before anything lands: an abandoned wizard would litter the
navigator with half-real entries, and "zero content persistence before
confirmation" is the trust posture #614 asks for. The Job payload is audit
state, not product content; candidates stay there until the explicit
confirm.

## Confirmation path: per-candidate creation, no batch endpoint

Two options were considered for confirmation: a new atomic batch endpoint,
or per-candidate reuse of the existing lorebook document creation route.

A batch endpoint would create a new atomicity contract (all-or-nothing?)
that no existing surface needs. Per-candidate creation keeps one atomic unit
per entry, matches the existing creation gates (title collision handling,
request validation constraints), and lets the wizard report each candidate's
result independently — a failed creation names its candidate, and the author
can retry just that one. **Chosen: per-candidate creation** with a per-row
result state in the wizard UI.

## Input budget and segmentation

The generation context capacity change fixed the discipline: fixed caps,
fail-closed stable errors, never silent truncation. The wizard applies the
same shape at its own boundary:

- Each input segment (one paste or one selected document's current content)
  is capped in Unicode code points. A segment over the cap is rejected
  before provider construction with a stable capacity envelope naming the
  limit; the author splits or trims the material.
- The assembled extraction prompt (fixed labels + segment content) counts
  against the same 8,388,608 UTF-8 byte authority as proposal generation.
- Segments extract independently; the wizard merges candidates by
  (kind, title) and keeps the union of suggested aliases. Deterministic
  merge order (reading order, then title) keeps repeated extractions
  stable.

Rationale for no auto-chunking: a silently chunked mega-paste would produce
candidates the author cannot map back to their material, and the capacity
precedent rejects silent reshaping of author input.

## Trial provider behavior

The mock provider is production-legal and is the default first-run
experience (#615). The wizard therefore must work on it: the mock path
returns deterministic placeholder candidates (fixed titles/bodies marked as
placeholders) and the UI labels the session with the same trial-mode
wording as the entry-page explainer. This keeps the onboarding loop whole
("paste → see candidates → confirm") with zero configuration, while the
provider-failure boundary still guards misconfigured real providers.

## Retrieval over existing content

The wizard's "select existing documents" path lists documents by kind and
reads current content through existing read services; it performs no
free-text search of its own. If a future iteration adds candidate-matching
search (e.g. "does this character already exist?"), it must go through
`buildFtsMatchQuery` + parameterized MATCH — the same red line recorded in
the proposal's Decisions and enforced by existing malicious-input coverage.

## Frontend placement

The wizard lives in the Inspector's Lore area as a guided flow reachable
from the empty-lorebook state (the primary onboarding moment) and from a
persistent entry point once entries exist (re-extraction for a growing
manuscript is a valid session, not just first-run). Route-backed activation
follows the existing Inspector URL contract; the wizard is one more
Inspector surface, not a new page shell.
