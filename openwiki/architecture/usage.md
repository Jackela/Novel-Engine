# Usage

The usage ledger aggregates per-project token consumption from persisted usage events. It is a project-level accounting surface with no document dimension: the reported totals are **cumulative over the project's entire history**, alongside a zero-filled trailing-30-UTC-day window for recent activity.

**Primary sources:** `server/src/contexts/studio/interface/http/job_routes.ts`, `server/src/contexts/studio/infrastructure/job_store_part.ts`.

## Endpoint contract

`GET /api/projects/:projectId/usage` returns, through the guard-protected route with a TypeBox response schema (`usageResponseSchema` in `server/src/contexts/studio/interface/http/job_schemas.ts`):

```text
{
  "project_id":        string,
  "request_count":     number,   // cumulative usage events
  "prompt_tokens":     number,   // cumulative
  "completion_tokens": number,   // cumulative
  "daily": [
    { "date": string, "request_count": number,
      "prompt_tokens": number, "completion_tokens": number }
  ],                 // trailing 30 UTC days, oldest first
  "per_model": [
    { "model": string, "requests": number,
      "prompt_tokens": number, "completion_tokens": number }
  ]
}
```

The three totals are honest reductions over `per_model` — the store aggregates usage events grouped by model inside a scoped transaction, then sums the per-model rows into `request_count`, `prompt_tokens`, and `completion_tokens` (`server/src/contexts/studio/infrastructure/job_store_part.ts`, `aggregateProjectUsage`). Per-model rows are ordered by model name. The application entry is `JobHistoryService.aggregateProjectUsage` (`server/src/contexts/studio/application/job_history_service.ts`).

## Where usage events come from

Each completed proposal generation (synchronous and streamed) records its job and usage event atomically through `recordCompletedProposalJob`; a retried proposal uses `markJobOutcomeWithUsage`. Both carry provider, model, prompt/completion tokens, and request evidence JSON (`server/src/contexts/studio/application/proposal_landing.ts`, `server/src/contexts/studio/application/job_retry_executor.ts`, `server/src/contexts/studio/infrastructure/job_store_part.ts`). When the provider reports no token counts, the deterministic fallback `resolvedTokenCount` derives them from the instruction and proposal text (`server/src/contexts/studio/application/proposal_landing.ts`). Reviews and exports do not write usage events; the export job's provider is the honest `studio` renderer label, not an AI model.

The Usage inspector consumes this endpoint through the shared API client. `useProjectUsage` loads it lazily when the Usage tab becomes active and exposes an explicit refresh; `StudioUsagePanel` renders the cumulative totals, trailing-30-day buckets, and per-model rows. Project ownership and cancellation prevent a previous project's response from publishing into the current workbench (`frontend/src/app/api.ts`, `frontend/src/features/studio/hooks/useProjectUsage.ts`, `frontend/src/features/studio/components/StudioUsagePanel.tsx`).

## Browser regression coverage

[`studio_usage.spec.ts`](../../frontend/tests/e2e-ts/workflows/studio_usage.spec.ts)
compares generated usage with the real API response, checks retained data and
focus after a failed refresh and recovery, and releases a delayed response
after switching projects to verify isolation. For a targeted run, include
`tests/e2e-ts/studio-ts.spec.ts` for Owner initialization. Follow the
[browser prerequisites](../quickstart.md#quick-validation) before running either
the targeted workflow or the full suite.
