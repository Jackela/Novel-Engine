import { randomUUID } from "node:crypto";

import { eq } from "drizzle-orm";

import type { StudioSqliteDatabase } from "../../../../shared/infrastructure/db/connection.js";
import { nextJobEventSequence } from "./job_event_sequence.js";
import { jobEvents, jobs } from "./schema.js";

/** The fixed restart error and event reason are contract surfaces; keep byte-identical. */
const RESTART_INTERRUPTED_ERROR = "Job lost its execution lease during process restart.";
const RESTART_EVENT_DETAILS = '{"reason":"execution_lease_lost_during_restart"}';

/**
 * Job-state restart recovery is row updates and event inserts only: every
 * running job becomes interrupted with the fixed restart error and one job
 * event naming the restart reason. Context-owned filesystem reconciliation
 * runs separately through the pre-recovery hook of the startup pipeline
 * (#534: injected into the shared opener by the studio persistence layer).
 */
export function recoverInterruptedJobs(db: StudioSqliteDatabase): number {
  const now = new Date();
  return db.transaction((tx) => {
    const running = tx.select({ id: jobs.id }).from(jobs).where(eq(jobs.status, "running")).all();
    for (const job of running) {
      const jobId = job.id;
      tx.update(jobs)
        .set({
          status: "interrupted",
          error: RESTART_INTERRUPTED_ERROR,
          updated_at: now,
          finished_at: now,
        })
        .where(eq(jobs.id, jobId))
        .run();
      tx.insert(jobEvents)
        .values({
          id: randomUUID(),
          job_id: jobId,
          status: "interrupted",
          details_json: RESTART_EVENT_DETAILS,
          sequence: nextJobEventSequence(tx, jobId),
          created_at: now,
        })
        .run();
    }
    return running.length;
  });
}
