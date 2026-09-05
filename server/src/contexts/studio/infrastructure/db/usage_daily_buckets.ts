import { and, eq, gte } from "drizzle-orm";

import { usageEvents } from "../../../../shared/infrastructure/db/schema.js";
import type { ProjectUsageDailyBucket } from "../../application/ports/project_usage.js";
import { addSafeUsage, assertSafeUsageToken } from "./safe_usage_tokens.js";
import type { Tx } from "./studio_query_helpers.js";

const DAY_MS = 86_400_000;
const WINDOW_DAYS = 30;

/**
 * The trailing-30-UTC-day usage buckets (#384): today included, zero-filled,
 * oldest first. Window events are read with a parameterized lower bound and
 * folded into UTC day keys in JS (no SQL date surgery on the integer
 * timestamp column).
 */
export function dailyUsageBuckets(tx: Tx, projectId: string, now: Date): ProjectUsageDailyBucket[] {
  const todayStart = Math.floor(now.getTime() / DAY_MS) * DAY_MS;
  const windowStart = new Date(todayStart - (WINDOW_DAYS - 1) * DAY_MS);
  const events = tx
    .select({
      createdAt: usageEvents.created_at,
      promptTokens: usageEvents.prompt_tokens,
      completionTokens: usageEvents.completion_tokens,
    })
    .from(usageEvents)
    .where(and(eq(usageEvents.project_id, projectId), gte(usageEvents.created_at, windowStart)))
    .all();
  const byDate = new Map<string, ProjectUsageDailyBucket>();
  for (let day = WINDOW_DAYS - 1; day >= 0; day -= 1) {
    const key = new Date(todayStart - day * DAY_MS).toISOString().slice(0, 10);
    byDate.set(key, { date: key, requestCount: 0, promptTokens: 0, completionTokens: 0 });
  }
  for (const event of events) {
    assertSafeUsageToken(event.promptTokens, "prompt");
    assertSafeUsageToken(event.completionTokens, "completion");
    const bucket = byDate.get(new Date(event.createdAt.getTime()).toISOString().slice(0, 10));
    if (bucket === undefined) {
      continue;
    }
    bucket.requestCount = addSafeUsage(bucket.requestCount, 1, "request");
    bucket.promptTokens = addSafeUsage(bucket.promptTokens, event.promptTokens, "prompt");
    bucket.completionTokens = addSafeUsage(
      bucket.completionTokens,
      event.completionTokens,
      "completion",
    );
  }
  return [...byDate.values()];
}
