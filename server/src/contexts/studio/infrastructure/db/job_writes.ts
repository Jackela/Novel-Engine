import { randomUUID } from "node:crypto";
import { eq } from "drizzle-orm";

import { jobEvents, jobs, usageEvents } from "../../../../shared/infrastructure/db/schema.js";
import type {
  AddJobInput,
  AddUsageEventInput,
  MarkJobOutcomeInput,
} from "../../application/ports/job_records.js";
import type { Tx } from "./studio_query_helpers.js";

/**
 * Row-level write helpers for the workflow jobs and usage ledger. Each one
 * runs inside a caller-owned transaction so combined landings (#392) can
 * commit the job row and its usage event together or not at all.
 */

/** Insert the job row plus its first event; returns the new job id. */
export function insertJobAndEvent(tx: Tx, input: AddJobInput): string {
  const job: typeof jobs.$inferInsert = {
    id: randomUUID(),
    project_id: input.projectId,
    document_id: input.documentId,
    kind: input.kind,
    operation: input.operation,
    status: input.status,
    provider: input.provider,
    model: input.model,
    request_json: input.requestJson,
    result_json: input.resultJson,
    error: input.error,
    created_at: input.now,
    updated_at: input.now,
  };
  tx.insert(jobs)
    .values({ ...job, retry_of_job_id: input.retryOfJobId ?? null })
    .run();
  tx.insert(jobEvents)
    .values({
      id: randomUUID(),
      job_id: job.id,
      status: input.status,
      details_json: input.eventDetailsJson,
      created_at: input.now,
    })
    .run();
  return job.id;
}

/** Insert one usage-ledger row. */
export function writeUsageEvent(tx: Tx, input: AddUsageEventInput): void {
  tx.insert(usageEvents)
    .values({
      id: randomUUID(),
      project_id: input.projectId,
      job_id: input.jobId,
      provider: input.provider,
      model: input.model,
      prompt_tokens: input.promptTokens,
      completion_tokens: input.completionTokens,
      request_evidence_json: input.requestEvidenceJson,
      estimated_cost: null,
      created_at: input.now,
    })
    .run();
}

/** Apply a terminal outcome transition and append its matching event. */
export function applyJobOutcome(tx: Tx, jobId: string, input: MarkJobOutcomeInput): void {
  tx.update(jobs)
    .set({
      status: input.status,
      ...(input.resultJson === undefined ? {} : { result_json: input.resultJson }),
      ...(input.model === undefined ? {} : { model: input.model }),
      error: input.error,
      updated_at: input.now,
      finished_at: input.now,
    })
    .where(eq(jobs.id, jobId))
    .run();
  tx.insert(jobEvents)
    .values({
      id: randomUUID(),
      job_id: jobId,
      status: input.status,
      details_json: input.eventDetailsJson,
      created_at: input.now,
    })
    .run();
}
