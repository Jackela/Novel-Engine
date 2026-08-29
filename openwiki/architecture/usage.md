# Usage

The usage ledger aggregates per-project token consumption from persisted usage events. It is a project-level accounting surface — there is no document dimension and no time dimension: the reported numbers are **cumulative totals over the project's entire history**, not a per-day or per-period series.

**Primary sources:** `server/src/contexts/studio/interface/http/job_routes.ts`, `server/src/contexts/studio/infrastructure/job_store_part.ts`.

## Endpoint contract

`GET /api/projects/:projectId/usage` returns, through the guard-protected route with a TypeBox response schema (`usageResponseSchema` in `server/src/contexts/studio/interface/http/job_schemas.ts`):

```text
{
  "project_id":        string,
  "request_count":     number,   // cumulative usage events
  "prompt_tokens":     number,   // cumulative
  "completion_tokens": number,   // cumulative
  "per_model": [
    { "model": string, "requests": number,
      "prompt_tokens": number, "completion_tokens": number }
  ]
}
```

The three totals are honest reductions over `per_model` — the store aggregates usage events grouped by model inside a scoped transaction, then sums the per-model rows into `request_count`, `prompt_tokens`, and `completion_tokens` (`server/src/contexts/studio/infrastructure/job_store_part.ts`, `aggregateProjectUsage`). Per-model rows are ordered by model name. The application entry is `JobHistoryService.aggregateProjectUsage` (`server/src/contexts/studio/application/job_history_service.ts`).

## Where usage events come from

Each proposal generation (synchronous, streamed, and retried alike) lands a usage event alongside its job through `store.addUsageEvent`, carrying provider, model, prompt/completion tokens, and request evidence JSON (`server/src/contexts/studio/infrastructure/job_store_part.ts`, `addUsageEvent`). When the provider reports no token counts, the deterministic fallback `resolvedTokenCount` derives them from the instruction and proposal text (`server/src/contexts/studio/application/proposal_landing.ts`). Reviews and exports do not write usage events; the export job's provider is the honest `studio` renderer label, not an AI model.

The frontend has **no consumer** of this endpoint yet: `frontend/src/app/api.ts` and `frontend/src/app/types/studio.ts` define no usage call or type, and the generated contract exists in `frontend/generated/api-types.ts`. Any future consumption must go through the shared API client (`openwiki/frontend/studio-workspace.md`, "API client behavior").
