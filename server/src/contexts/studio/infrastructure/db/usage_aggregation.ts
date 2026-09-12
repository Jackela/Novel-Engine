import { asc, eq, sql } from "drizzle-orm";

import { usageEvents } from "../../../../shared/infrastructure/db/schema.js";
import type { ProjectUsageAggregate } from "../../application/ports/project_usage.js";
import { addSafeUsage, safeUsageAggregate } from "./safe_usage_tokens.js";
import type { Tx } from "./studio_query_helpers.js";
import { dailyUsageBuckets } from "./usage_daily_buckets.js";

/**
 * The usage-ledger aggregation (#317): totals over the project's usage
 * events plus a per-model breakdown. `daily` (#384) adds the
 * trailing-30-UTC-day buckets relative to `now`. The caller re-verifies
 * principal scoping before this read.
 */
export function projectUsageAggregate(tx: Tx, projectId: string, now: Date): ProjectUsageAggregate {
  const rows = tx
    .select({
      model: usageEvents.model,
      requests: sql<string>`CAST(COUNT(*) AS TEXT)`,
      promptTokens: sql<string>`CAST(SUM(${usageEvents.prompt_tokens}) AS TEXT)`,
      completionTokens: sql<string>`CAST(SUM(${usageEvents.completion_tokens}) AS TEXT)`,
    })
    .from(usageEvents)
    .where(eq(usageEvents.project_id, projectId))
    .groupBy(usageEvents.model)
    .orderBy(asc(usageEvents.model))
    .all();
  const perModel = rows.map((row) => ({
    model: row.model,
    requests: safeUsageAggregate(row.requests, "request"),
    promptTokens: safeUsageAggregate(row.promptTokens, "prompt"),
    completionTokens: safeUsageAggregate(row.completionTokens, "completion"),
  }));
  return {
    projectId,
    requestCount: perModel.reduce(
      (total, entry) => addSafeUsage(total, entry.requests, "request"),
      0,
    ),
    promptTokens: perModel.reduce(
      (total, entry) => addSafeUsage(total, entry.promptTokens, "prompt"),
      0,
    ),
    completionTokens: perModel.reduce(
      (total, entry) => addSafeUsage(total, entry.completionTokens, "completion"),
      0,
    ),
    perModel,
    daily: dailyUsageBuckets(tx, projectId, now),
  };
}
