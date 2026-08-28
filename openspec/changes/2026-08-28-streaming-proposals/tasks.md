# Tasks

- [ ] 1. Port: optional `generateStructuredStreaming` capability with delta
      contract and stream options (signal, outcome callback)
- [ ] 2. Deterministic provider streams fixed prose in word groups; join of
      deltas equals the synchronous output
- [ ] 3. DashScope + OpenAI-compatible adapters stream SSE chunks
      (`incremental_output` / `stream=true`), pass abort signals upstream,
      and report final-chunk usage
- [ ] 4. `AiProposalService.draftProposalStream` with synchronous-parity
      landing (completed job + one usage event, failed job, abort persists
      nothing)
- [ ] 5. `POST .../ai-proposals/stream` SSE endpoint with envelope errors
      before the stream and delta/done/error frames on it
- [ ] 6. Frontend streaming client (fetch + ReadableStream, credentials +
      CSRF unchanged) and progressive proposal preview with Stop
- [ ] 7. Server tests (provider chunking, adapter SSE parsing, service
      landing, route frame sequence, abort persistence) and frontend tests
      (frame parser, hook streaming/stop transitions)
- [ ] 8. Regenerate the OpenAPI baseline + frontend api-types for the new
      route
