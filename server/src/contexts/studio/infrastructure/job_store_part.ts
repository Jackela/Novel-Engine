import { randomUUID } from "node:crypto";
import { asc, desc, eq, inArray } from "drizzle-orm";

import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import { jobEvents, jobs, usageEvents } from "../../../shared/infrastructure/db/schema.js";
import type {
  AddJobInput,
  AddUsageEventInput,
  JobRecord,
  MarkJobOutcomeInput,
  ProjectScope,
} from "../application/ports/studio_store.js";
import { NotFoundError } from "../domain/exceptions.js";
import { type ProjectRow, scopedProject, type Tx } from "./db/studio_query_helpers.js";

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

function jobWithEvents(tx: Tx, jobId: string): JobRecord {
  const job = tx.select().from(jobs).where(eq(jobs.id, jobId)).get();
  if (job === undefined) {
    throw new NotFoundError("Job not found.");
  }
  const events = tx
    .select()
    .from(jobEvents)
    .where(eq(jobEvents.job_id, jobId))
    .orderBy(asc(jobEvents.created_at))
    .all();
  return toJobRecord(job, events);
}

/**
 * The workflow half of the Drizzle studio store: proposal jobs with their
 * event trail and the usage accounting rows. Jobs reference projects by a
 * plain column (the studio tables live in another schema module), so every
 * access re-verifies principal scoping through the projects table first.
 */
export class JobStorePart {
  protected readonly db: StudioSqliteDatabase;

  constructor(db: StudioSqliteDatabase) {
    this.db = db;
  }

  addJob(scope: ProjectScope, input: AddJobInput): JobRecord {
    return this.db.transaction((tx) => {
      scopedProject(tx, scope, input.projectId);
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
      return jobWithEvents(tx, job.id);
    });
  }

  addUsageEvent(scope: ProjectScope, input: AddUsageEventInput): void {
    this.db.transaction((tx) => {
      scopedProject(tx, scope, input.projectId);
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
    });
  }

  findJob(scope: ProjectScope, projectId: string, jobId: string): JobRecord {
    return this.db.transaction((tx) => {
      const project: ProjectRow = scopedProject(tx, scope, projectId);
      const job = tx.select().from(jobs).where(eq(jobs.id, jobId)).get();
      if (job === undefined || job.project_id !== project.id) {
        throw new NotFoundError("Job not found.");
      }
      return jobWithEvents(tx, job.id);
    });
  }

  /**
   * The audit-trail listing: jobs newest first, and within each job the
   * events newest first (the OpenSpec listing contract).
   */
  collectProjectJobs(scope: ProjectScope, projectId: string): JobRecord[] {
    return this.db.transaction((tx) => {
      const project: ProjectRow = scopedProject(tx, scope, projectId);
      const rows = tx
        .select()
        .from(jobs)
        .where(eq(jobs.project_id, project.id))
        .orderBy(desc(jobs.created_at))
        .all();
      if (rows.length === 0) {
        return [];
      }
      const events = tx
        .select()
        .from(jobEvents)
        .where(
          inArray(
            jobEvents.job_id,
            rows.map((row) => row.id),
          ),
        )
        .orderBy(desc(jobEvents.created_at))
        .all();
      const eventsByJob = new Map<string, JobEventRow[]>();
      for (const event of events) {
        const bucket = eventsByJob.get(event.job_id) ?? [];
        bucket.push(event);
        eventsByJob.set(event.job_id, bucket);
      }
      return rows.map((row) => toJobRecord(row, eventsByJob.get(row.id) ?? []));
    });
  }

  markJobOutcome(
    scope: ProjectScope,
    projectId: string,
    jobId: string,
    input: MarkJobOutcomeInput,
  ): JobRecord {
    return this.db.transaction((tx) => {
      scopedProject(tx, scope, projectId);
      const job = tx.select().from(jobs).where(eq(jobs.id, jobId)).get();
      if (job === undefined || job.project_id !== projectId) {
        throw new NotFoundError("Job not found.");
      }
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
      return jobWithEvents(tx, jobId);
    });
  }

  setJobResult(
    scope: ProjectScope,
    projectId: string,
    jobId: string,
    resultJson: string,
    now: Date,
  ): JobRecord {
    return this.db.transaction((tx) => {
      scopedProject(tx, scope, projectId);
      const job = tx.select().from(jobs).where(eq(jobs.id, jobId)).get();
      if (job === undefined || job.project_id !== projectId) {
        throw new NotFoundError("Job not found.");
      }
      tx.update(jobs)
        .set({ result_json: resultJson, updated_at: now })
        .where(eq(jobs.id, jobId))
        .run();
      return jobWithEvents(tx, jobId);
    });
  }
}
