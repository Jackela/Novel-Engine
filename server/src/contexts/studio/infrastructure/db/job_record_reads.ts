import { asc, eq } from "drizzle-orm";

import { jobEvents, jobs } from "../../../../shared/infrastructure/db/schema.js";
import type { JobRecord } from "../../application/ports/job_records.js";
import { NotFoundError } from "../../domain/exceptions.js";
import type { Tx } from "./studio_query_helpers.js";

type JobRow = typeof jobs.$inferSelect;
type JobEventRow = typeof jobEvents.$inferSelect;

function toJobRecord(job: JobRow, events: JobEventRow[]): JobRecord {
  return {
    id: job.id,
    projectId: job.project_id,
    documentId: job.document_id,
    kind: job.kind,
    operation: job.operation,
    status: job.status,
    provider: job.provider,
    model: job.model,
    requestJson: job.request_json,
    resultJson: job.result_json,
    error: job.error,
    retryOfJobId: job.retry_of_job_id,
    createdAt: job.created_at,
    updatedAt: job.updated_at,
    events: events.map((event) => ({
      id: event.id,
      jobId: event.job_id,
      status: event.status,
      detailsJson: event.details_json,
      createdAt: event.created_at,
    })),
  };
}

export function jobWithEvents(tx: Tx, jobId: string): JobRecord {
  const job = tx.select().from(jobs).where(eq(jobs.id, jobId)).get();
  if (job === undefined) throw new NotFoundError("Job not found.");
  const events = tx
    .select()
    .from(jobEvents)
    .where(eq(jobEvents.job_id, jobId))
    .orderBy(asc(jobEvents.sequence))
    .all();
  return toJobRecord(job, events);
}
