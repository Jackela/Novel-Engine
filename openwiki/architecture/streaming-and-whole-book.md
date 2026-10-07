# Streaming and the whole-book loop

Two capabilities ride on top of the same proposal pipeline: the SSE stream that shows proposal markdown as it is generated, and the frontend-driven loop that drafts and accepts one chapter after another until the whole book has accepted AI revisions.

**Primary sources:** `server/src/contexts/studio/application/proposal_streaming.ts`, `server/src/contexts/studio/interface/http/proposal_routes.ts`, `frontend/src/app/proposalStream.ts`, `frontend/src/features/studio/hooks/wholeBookPlan.ts`.

## SSE proposal stream

`POST /api/projects/:projectId/documents/:documentId/ai-proposals/stream` is the streaming twin of the synchronous proposal endpoint: same request body, identical job and usage landing, identical in-flight guarding. Validation errors, unknown documents, an in-flight conflict (`409`), and providers without the streaming capability all resolve **before the first frame**, answered with the normal error envelope. Only then does the reply hijack into a `text/event-stream` response (`server/src/contexts/studio/interface/http/proposal_routes.ts`).

The frame vocabulary is closed — one JSON object per `data:` line, blank-line terminated (`ProposalStreamFrame` in `proposal_streaming.ts`):

- `{"type":"delta","text":"..."}` — the next piece of proposal markdown as the provider writes it.
- `{"type":"done","job":{...}}` — the completed proposal job, the same payload the synchronous endpoint returns.
- `{"type":"error","error":{"code":"PROVIDER_FAILED","message":"..."}}` — a provider failure (connect, mid-stream, or prose rejected after completion) lands a failed job exactly like the synchronous path, then ends the stream.

Alongside these frames the server writes a `: heartbeat` comment frame every
15 seconds while a generation is silent, so proxies and clients do not treat
the idle connection as dead; comment frames carry no `data:` field
(`HEARTBEAT_FRAME` / `DEFAULT_HEARTBEAT_MS` in
`server/src/contexts/studio/interface/http/proposal_stream_response.ts`).
Clients must ignore every frame that is not a `data:` frame — the shipped
parser already drops them (`parseFrameEvent` in
`frontend/src/app/proposalStream.ts`).

The frontend consumes the stream with `fetch` + `ReadableStream` so credentials and the CSRF header stay identical to the synchronous client, using the incremental `ProposalStreamParser`; received deltas land in the Copilot panel preview only — the manuscript changes through explicit accept, never the stream (`frontend/src/app/proposalStream.ts`, `frontend/src/features/studio/hooks/useStudioProposal.ts`, `frontend/src/features/studio/components/StudioCopilotPanel.tsx`). Each manual stream belongs to one project/document identity and request epoch. Changing either identity aborts the current controller, clears that owner's pending state, and prevents late delta, job, or error publication into the new document.

## Stoppable and resumable

**Abort.** A closed or errored client connection aborts the upstream provider stream through a disconnect `AbortController`; an aborted proposal **persists nothing at all** — no job, no usage event (`proposal_routes.ts`, `proposal_streaming.ts`). The same signal is exposed to callers: the frontend passes an `AbortController` so cancelling a streamed draft leaves no trace server-side.

**The whole-book loop.** `useWholeBookLoop` is a frontend state machine over `streamProposal` plus the atomic accept endpoint: `idle` → `running(current,total)` → `done(generated,stoppedEarly)` | `failed(generated,failedChapterTitle,message)`. The plan comes from `wholeBookPlan` (`frontend/src/features/studio/hooks/wholeBookPlan.ts`): a chapter is a candidate iff its current revision's source is not `ai-accepted`, then split by emptiness — empty chapters may be drafted and auto-accepted right away, while chapters that already hold text the author did not accept from AI (seeded, hand-written, imported, or restored) are replaced only after an explicit per-run confirmation (DR-007). Chapters run strictly sequentially — each streamed draft depends on the previous accept — and the plan is **recomputed from persisted documents at every start**, which is what makes the loop resumable: after a stop or failure, starting again proceeds with the empty chapters and re-asks for confirmation on chapters still holding unconfirmed text.

One run captures the project identity and a monotonically changing epoch. Stop marks that run stopped and aborts its in-flight proposal controller, so the server lands no job or usage event for that unfinished draft; the loop then starts no later chapter. If atomic acceptance has already started, it may complete on the server and remains an immutable accepted chapter. While the same project workbench remains mounted, its guarded aggregate refresh reconciles that committed chapter even if the active document changed; only a matching document owner may reset editor state. A project change invalidates the epoch and aborts the cancellable post-accept refresh, so the next project cannot receive the old aggregate. This is why cancellation is described separately from atomic acceptance rather than as a rollback.

During the run, generation lands with `chapter_number: document.position` in job metadata (`server/src/contexts/studio/application/proposal_landing.ts`), and reading order follows ADR-0005: volume position first, then in-volume chapter position. `StudioWholeBookControl` renders the plan hint, the dry-run confirmation list for occupied chapters, a polite `role="status"` progress line, a visible stop control while running, and the preserved-work outcome (`frontend/src/features/studio/components/StudioWholeBookControl.tsx`), embedded in the navigator on the manuscript surface.
