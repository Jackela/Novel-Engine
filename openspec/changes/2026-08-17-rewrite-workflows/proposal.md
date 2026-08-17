# Rewrite slice 3 — workflows

## Why

The TypeScript greenfield rewrite (ADR-0001/0002) is chartered, and the
adjudicated workflow decisions (wayfinder map #242; tickets #248, #249,
#252) now need a home in the `novel-engine` capability specification. The
audit found the workflow layer living almost entirely in code (audit
§4.4–§4.6: D2–D6, D9–D11, D14, E1–E6, F1–F3, B13–B15) — including the
F-1/#240 failure mode where every gate stayed green while the mock provider
returned echo residue instead of prose.

## What Changes

- Adds the workflow Requirements to `novel-engine`: explicit AI proposals
  with idempotent acceptance; the server-side operation-to-step mapping with
  a closed step vocabulary and the prose-content guarantee; the untrusted
  manuscript boundary and both sanitization lists as single-source data;
  provider behavior contracts (explicit unconfigured failure, server-side
  model resolution, shared structured-field retry with the 180-second floor,
  per-request lifecycle); snapshot-bound deterministic review; snapshot-bound
  export with reuse plus the markdown/DOCX/EPUB format contracts and
  project-scoped artifacts; the synchronous job execution model with restart
  recovery and the retry chain; and read-only idempotent legacy import.
- Absorbs the three workflow Requirements of `novel-studio` — Explicit AI
  proposals, Snapshot-bound review and export, Durable jobs — as rewritten
  Requirements with the adjudicated deviations folded in: jobs are a
  synchronous audit log (F1+G2), exports are deleted with their project
  (D4), and providers fail loudly on unknown steps instead of echoing (D14).
- Coordinates with slice 1 (the unified error envelope and the request
  validation constraints these workflows answer in) and slice 2 (the
  immutable snapshots and revisions that review and export bind to; the
  no-invented-lease rule this slice's restart-recovery clause mirrors).

Deliberate non-goals: no background executor, queue, lease, heartbeat, or
worker registration — any move to asynchronous execution is a new decision
that must jointly reopen the frontend behavior contract; no retention, TTL,
or GC job for live projects' export files; no rich-format DOCX/EPUB
conversion (stripped plain text only); the HTTP operation enum stays
`continue`/`rewrite`/`generate` with no provider-step vocabulary leaking
into the API.

## Impact

- New Requirements in the `novel-engine` capability; `novel-studio` stays
  valid and is retired only by the cutover change.
- Feeds the #252 cutover-blocking acceptance surface: prose-proposal
  content assertions (the F-1/#240 guard), markdown export byte-fidelity,
  DOCX/EPUB structural checks, export-directory deletion on project delete,
  unconfigured-provider loud failure, unknown-step rejection, import symlink
  rejection, and retry gating.
- Implementation direction carried by the decisions: exporters move to the
  npm `docx` package and a minimal jszip-based EPUB writer; retry decisions
  read structured error fields through one shared module.
