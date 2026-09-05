import { randomUUID } from "node:crypto";
import { and, eq } from "drizzle-orm";

import { jobEvents, jobs } from "../../../../shared/infrastructure/db/schema.js";
import type { Tx } from "./studio_query_helpers.js";

type JobRow = typeof jobs.$inferSelect;

const RETRY_IDEMPOTENCY_CONSTRAINT =
  "UNIQUE constraint failed: jobs.project_id, jobs.retry_of_job_id, jobs.retry_idempotency_key";

export interface RetryClaimRow {
  readonly jobId: string;
  readonly created: boolean;
}

export function findRetryJobByKey(
  tx: Tx,
  projectId: string,
  sourceJobId: string,
  requestKey: string,
): JobRow | undefined {
  return tx
    .select()
    .from(jobs)
    .where(
      and(
        eq(jobs.project_id, projectId),
        eq(jobs.retry_of_job_id, sourceJobId),
        eq(jobs.retry_idempotency_key, requestKey),
      ),
    )
    .get();
}

export function insertRetryClaim(
  tx: Tx,
  source: JobRow,
  requestKey: string,
  now: Date,
  beforeEventInsert: (jobId: string) => void,
): RetryClaimRow {
  const jobId = randomUUID();
  try {
    tx.insert(jobs)
      .values({
        id: jobId,
        project_id: source.project_id,
        document_id: source.document_id,
        kind: source.kind,
        operation: source.operation,
        status: "running",
        provider: source.provider,
        model: source.model,
        request_json: source.request_json,
        result_json: "{}",
        error: null,
        retry_of_job_id: source.id,
        retry_idempotency_key: requestKey,
        created_at: now,
        updated_at: now,
      })
      .run();
  } catch (error) {
    if (!isRetryIdempotencyConflict(error)) throw error;
    const winner = findRetryJobByKey(tx, source.project_id, source.id, requestKey);
    if (winner === undefined) throw error;
    return { jobId: winner.id, created: false };
  }

  beforeEventInsert(jobId);
  tx.insert(jobEvents)
    .values({
      id: randomUUID(),
      job_id: jobId,
      status: "running",
      details_json: JSON.stringify({ retry_of: source.id }),
      sequence: 1,
      created_at: now,
    })
    .run();
  return { jobId, created: true };
}

function isRetryIdempotencyConflict(error: unknown): boolean {
  return (
    error !== null &&
    typeof error === "object" &&
    (error as { code?: unknown }).code === "SQLITE_CONSTRAINT_UNIQUE" &&
    (error as { message?: unknown }).message === RETRY_IDEMPOTENCY_CONSTRAINT
  );
}
