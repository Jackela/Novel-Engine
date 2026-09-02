import { and, desc, eq, inArray, sql } from "drizzle-orm";

import { jobEvents, jobs } from "../../../shared/infrastructure/db/schema.js";
import type { JobPageInput } from "../application/ports/job_records.js";
import type { Tx } from "./db/studio_query_helpers.js";

/** Build the exact keyset query executed by the project job listing. */
export function buildProjectJobsPageQuery(tx: Tx, projectId: string, input: JobPageInput) {
  const cursorRange =
    input.cursor === undefined
      ? undefined
      : sql`(${jobs.created_at}, ${jobs.id}) < (${input.cursor.createdAtMs}, ${input.cursor.id})`;
  return tx
    .select()
    .from(jobs)
    .where(and(eq(jobs.project_id, projectId), cursorRange))
    .orderBy(desc(jobs.created_at), desc(jobs.id))
    .limit(input.limit + 1);
}

/** Build the bounded event hydration query for one returned job page. */
export function buildJobEventsQuery(tx: Tx, jobIds: string[]) {
  return tx
    .select()
    .from(jobEvents)
    .where(inArray(jobEvents.job_id, jobIds))
    .orderBy(desc(jobEvents.job_id), desc(jobEvents.sequence));
}
