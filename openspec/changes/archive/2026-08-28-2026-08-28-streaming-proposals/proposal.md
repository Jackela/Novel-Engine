# Change: Streaming proposal generation (SSE)

## Why

Ticket #308. The proposal pipeline answers only after the provider finishes,
so the author stares at a spinner while the model writes. With the
context-assembly epic landed (#314/#315), the prompt carries real story
context, so streaming now delivers meaningful prose earlier instead of
amnesiac text faster (the original reason #308 was deferred).

## What Changes

- The text-generation port gains an optional streaming capability
  (`generateStructuredStreaming`, raw chapter-markdown deltas; concatenation
  of deltas is the full markdown), implemented by the deterministic provider
  (chunked prose) and both HTTP adapters (SSE passthrough with
  `stream=true` / DashScope `incremental_output`, abort-signal passthrough,
  usage read from the final stream chunk when present).
- A streaming service pipeline mirrors the synchronous landing: completed
  streams persist a completed job plus ONE usage event; provider failures
  persist a failed job; invalid prose after a stream fails the job without
  fabricated text; a client abort persists nothing.
- A new `POST /api/projects/:projectId/documents/:documentId/ai-proposals/stream`
  endpoint answers with `text/event-stream` frames
  (`delta`/`done`/`error`). Validation and unconfigured-provider errors
  answer with the normal error envelope before the stream starts. The
  synchronous endpoint is untouched (retries, whole-book loop, e2e
  determinism keep using it).
- The Studio copilot renders the streamed markdown progressively in the
  proposal preview with a Stop affordance; accept flow stays byte-identical.

## Impact

- Extends the `novel-engine` capability with one ADDED requirement
  (streaming proposal generation).
- Affected code: `server/src/contexts/ai/**` (port + providers),
  `server/src/contexts/studio/**` (proposal service + routes),
  `frontend/src/app/proposalStream.ts`, copilot panel and proposal hook.
- OpenAPI baseline and generated frontend api-types regenerated.
- Out of scope: token-cost optimization (standing adjudication), token-level
  streaming into the editor (proposals never mutate the manuscript directly).
