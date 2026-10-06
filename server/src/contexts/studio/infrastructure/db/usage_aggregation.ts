import { asc, eq, sql } from "drizzle-orm";
import type { ProjectUsageAggregate } from "../../application/ports/project_usage.js";
import { addSafeUsage, safeUsageAggregate } from "./safe_usage_tokens.js";
import { usageEvents } from "./schema.js";
import type { Tx } from "./studio_query_helpers.js";
import { dailyUsageBuckets } from "./usage_daily_buckets.js";

/**
 * The usage-ledger aggregation (#317, DR-028): totals over the project's
 * `completed` usage rows plus a per-model breakdown that also reports failed
 * attempts and estimated token provenance. Token sums are guarded by the same
 * exact-integer folding as before, so a failed attempt (zero tokens) can never
 * distort them. `daily` (#384) adds the trailing-30-UTC-day buckets relative
 * to `now`. The caller re-verifies principal scoping before this read.
 */
export function projectUsageAggregate(tx: Tx, projectId: string, now: Date): ProjectUsageAggregate {
  const rows = tx
    .select({
      model: usageEvents.model,
      requests: sql<string>`CAST(SUM(CASE WHEN ${usageEvents.outcome} = 'completed' THEN 1 ELSE 0 END) AS TEXT)`,
      failedAttempts: sql<string>`CAST(SUM(CASE WHEN ${usageEvents.outcome} = 'failed' THEN 1 ELSE 0 END) AS TEXT)`,
      estimatedRequests: sql<string>`CAST(SUM(CASE WHEN ${usageEvents.outcome} = 'completed' AND ${usageEvents.token_source} = 'estimated' THEN 1 ELSE 0 END) AS TEXT)`,
      promptTokens: sql<string>`CAST(SUM(CASE WHEN ${usageEvents.outcome} = 'completed' THEN ${usageEvents.prompt_tokens} ELSE 0 END) AS TEXT)`,
      completionTokens: sql<string>`CAST(SUM(CASE WHEN ${usageEvents.outcome} = 'completed' THEN ${usageEvents.completion_tokens} ELSE 0 END) AS TEXT)`,
    })
    .from(usageEvents)
    .where(eq(usageEvents.project_id, projectId))
    .groupBy(usageEvents.model)
    .orderBy(asc(usageEvents.model))
    .all();
  const perModel = rows.map((row) => ({
    model: row.model,
    requests: safeUsageAggregate(row.requests, "request"),
    failedAttempts: safeUsageAggregate(row.failedAttempts, "failed attempt"),
    estimatedRequests: safeUsageAggregate(row.estimatedRequests, "estimated request"),
    promptTokens: safeUsageAggregate(row.promptTokens, "prompt"),
    completionTokens: safeUsageAggregate(row.completionTokens, "completion"),
  }));
  const fold = (select: (entry: (typeof perModel)[number]) => number, label: string) =>
    perModel.reduce((total, entry) => addSafeUsage(total, select(entry), label), 0);
  return {
    projectId,
    requestCount: fold((entry) => entry.requests, "request"),
    failedAttemptCount: fold((entry) => entry.failedAttempts, "failed attempt"),
    estimatedRequestCount: fold((entry) => entry.estimatedRequests, "estimated request"),
    promptTokens: fold((entry) => entry.promptTokens, "prompt"),
    completionTokens: fold((entry) => entry.completionTokens, "completion"),
    perModel,
    daily: dailyUsageBuckets(tx, projectId, now),
  };
}
