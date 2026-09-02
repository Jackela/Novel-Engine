import { eq, max } from "drizzle-orm";

import type { StudioSqliteDatabase } from "./connection.js";
import { jobEvents } from "./schema.js";

type StudioTransaction = Parameters<Parameters<StudioSqliteDatabase["transaction"]>[0]>[0];

/** Allocate the next causal position inside one job's transaction-owned event log. */
export function nextJobEventSequence(tx: StudioTransaction, jobId: string): number {
  const latest = tx
    .select({ value: max(jobEvents.sequence) })
    .from(jobEvents)
    .where(eq(jobEvents.job_id, jobId))
    .get();
  return (latest?.value ?? 0) + 1;
}
