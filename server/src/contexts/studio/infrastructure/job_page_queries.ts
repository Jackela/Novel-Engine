import { and, desc, eq, isNotNull, sql } from "drizzle-orm";
import type { JobPageInput } from "../application/ports/job_records.js";
import { jobs } from "./db/schema.js";
import type { Tx } from "./db/studio_query_helpers.js";

/** Build the exact keyset query executed by the project job listing. */
export function buildProjectJobSummariesQuery(tx: Tx, projectId: string, input: JobPageInput) {
  const cursorRange =
    input.cursor === undefined
      ? undefined
      : sql`(${jobs.created_at}, ${jobs.id}) < (${input.cursor.createdAtMs}, ${input.cursor.id})`;
  return tx
    .select({
      id: jobs.id,
      projectId: jobs.project_id,
      documentId: jobs.document_id,
      kind: jobs.kind,
      operation: jobs.operation,
      status: jobs.status,
      provider: jobs.provider,
      model: jobs.model,
      error: jobs.error,
      retryOfJobId: jobs.retry_of_job_id,
      createdAt: jobs.created_at,
      updatedAt: jobs.updated_at,
    })
    .from(jobs)
    .where(and(eq(jobs.project_id, projectId), cursorRange))
    .orderBy(desc(jobs.created_at), desc(jobs.id))
    .limit(input.limit + 1);
}

/**
 * The diagnostics export's failure scan (#654): failed Jobs only, newest
 * terminal transition first, parameterized and bounded.
 */
export function buildRecentFailedJobErrorsQuery(tx: Tx, projectId: string, limit: number) {
  return tx
    .select({ error: jobs.error, updatedAt: jobs.updated_at })
    .from(jobs)
    .where(and(eq(jobs.project_id, projectId), eq(jobs.status, "failed"), isNotNull(jobs.error)))
    .orderBy(desc(jobs.updated_at), desc(jobs.id))
    .limit(limit);
}
