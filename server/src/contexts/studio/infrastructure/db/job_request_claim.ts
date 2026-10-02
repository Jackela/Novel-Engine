import { and, eq } from "drizzle-orm";

import type { AddJobInput } from "../../application/ports/job_records.js";
import { insertJobAndEvent, type JobInsert } from "./job_writes.js";
import { jobs } from "./schema.js";
import type { Tx } from "./studio_query_helpers.js";

type JobRow = typeof jobs.$inferSelect;

const REQUEST_IDEMPOTENCY_CONSTRAINT =
  "UNIQUE constraint failed: jobs.project_id, jobs.request_idempotency_key";

/**
 * Durable request-key dedupe for first-run generation landings (DR-027),
 * mirroring the retry claim in `job_retry_claim.ts`: the mutation carries an
 * optional client key, and the partial unique index on
 * (project_id, request_idempotency_key) makes the jobs table the single
 * authority — one key, at most one job row, one usage event, surviving
 * restarts. A duplicate whose lookup missed (concurrent insert) loses the
 * unique-index race and rejoins the winner instead of failing; the caller
 * skips its usage write for `created: false`.
 */

/** The job a request key already claimed in this project, if any. */
export function findRequestKeyJob(
  tx: Tx,
  projectId: string,
  requestKey: string,
): JobRow | undefined {
  return tx
    .select()
    .from(jobs)
    .where(and(eq(jobs.project_id, projectId), eq(jobs.request_idempotency_key, requestKey)))
    .get();
}

/**
 * Claim the landing row for `requestKey`: insert it (plus its first event) as
 * the winner, or rejoin the row an interleaved duplicate already inserted.
 * Failure semantics: only the exact request-idempotency unique violation is
 * converted into a replay; every other error stays visible to the caller, and
 * an unresolvable conflict rethrows the original insert error instead of
 * fabricating a winner.
 */
export function claimRequestKeyJob(
  tx: Tx,
  input: AddJobInput,
  requestKey: string,
  beforeEventInsert: (jobId: string) => void = () => {},
): JobInsert {
  try {
    const jobId = insertJobAndEvent(
      tx,
      { ...input, requestIdempotencyKey: requestKey },
      beforeEventInsert,
    );
    return { jobId, created: true };
  } catch (error) {
    if (!isRequestIdempotencyConflict(error)) throw error;
    const winner = findRequestKeyJob(tx, input.projectId, requestKey);
    if (winner === undefined) throw error;
    return { jobId: winner.id, created: false };
  }
}

function isRequestIdempotencyConflict(error: unknown): boolean {
  return (
    error !== null &&
    typeof error === "object" &&
    (error as { code?: unknown }).code === "SQLITE_CONSTRAINT_UNIQUE" &&
    (error as { message?: unknown }).message === REQUEST_IDEMPOTENCY_CONSTRAINT
  );
}
