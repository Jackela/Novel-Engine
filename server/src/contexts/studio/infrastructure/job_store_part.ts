import { asc, count, eq, sum } from "drizzle-orm";

import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import { jobEvents, jobs, usageEvents } from "../../../shared/infrastructure/db/schema.js";
import {
  type JobPageInput,
  type JobSummaryPage,
  jobPageLimit,
} from "../application/ports/job_records.js";
import type {
  AddJobInput,
  AddUsageEventInput,
  CompleteJobWithUsageInput,
  JobRecord,
  MarkJobOutcomeInput,
  ProjectScope,
  ProjectUsageAggregate,
  RecordCompletedProposalJobInput,
} from "../application/ports/studio_store.js";
import { InvalidJobTransitionError, NotFoundError } from "../domain/exceptions.js";
import {
  applyJobOutcome,
  insertJobAndEvent,
  writeUsageEvent as writeUsageEventRow,
} from "./db/job_writes.js";
import { type ProjectRow, scopedProject, type Tx } from "./db/studio_query_helpers.js";
import { dailyUsageBuckets } from "./db/usage_daily_buckets.js";
import { buildProjectJobSummariesQuery } from "./job_page_queries.js";

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
  if (job === undefined) {
    throw new NotFoundError("Job not found.");
  }
  const events = tx
    .select()
    .from(jobEvents)
    .where(eq(jobEvents.job_id, jobId))
    .orderBy(asc(jobEvents.sequence))
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
      const jobId = insertJobAndEvent(tx, input);
      return jobWithEvents(tx, jobId);
    });
  }

  addUsageEvent(scope: ProjectScope, input: AddUsageEventInput): void {
    this.db.transaction((tx) => {
      scopedProject(tx, scope, input.projectId);
      this.writeUsageEvent(tx, input);
    });
  }

  /**
   * The atomic completed-proposal landing (#392): the job row and its usage
   * event share one transaction, so a failure between the writes rolls back
   * both and never strands a completed job without its usage event.
   */
  recordCompletedProposalJob(
    scope: ProjectScope,
    input: RecordCompletedProposalJobInput,
  ): JobRecord {
    return this.db.transaction((tx) => {
      scopedProject(tx, scope, input.job.projectId);
      const jobId = insertJobAndEvent(tx, input.job);
      this.writeUsageEvent(tx, {
        ...input.usage,
        projectId: input.job.projectId,
        jobId,
        now: input.job.now,
      });
      return jobWithEvents(tx, jobId);
    });
  }

  /**
   * The atomic retry completion (#392): the terminal transition of the
   * running job and its usage event share one transaction.
   */
  markJobOutcomeWithUsage(
    scope: ProjectScope,
    projectId: string,
    jobId: string,
    input: CompleteJobWithUsageInput,
  ): JobRecord {
    return this.db.transaction((tx) => {
      scopedProject(tx, scope, projectId);
      this.assertOpenTransition(tx, projectId, jobId, input.outcome.status);
      applyJobOutcome(tx, jobId, input.outcome);
      this.writeUsageEvent(tx, {
        ...input.usage,
        projectId,
        jobId,
        now: input.outcome.now,
      });
      return jobWithEvents(tx, jobId);
    });
  }

  /**
   * The usage-ledger aggregation (#317): totals over the project's usage
   * events plus a per-model breakdown, read inside a scoped transaction.
   * `daily` (#384) adds the trailing-30-UTC-day buckets relative to `now`.
   */
  aggregateProjectUsage(scope: ProjectScope, projectId: string, now: Date): ProjectUsageAggregate {
    return this.db.transaction((tx) => {
      scopedProject(tx, scope, projectId);
      const rows = tx
        .select({
          model: usageEvents.model,
          requests: count(),
          promptTokens: sum(usageEvents.prompt_tokens),
          completionTokens: sum(usageEvents.completion_tokens),
        })
        .from(usageEvents)
        .where(eq(usageEvents.project_id, projectId))
        .groupBy(usageEvents.model)
        .orderBy(asc(usageEvents.model))
        .all();
      const perModel = rows.map((row) => ({
        model: row.model,
        requests: row.requests,
        promptTokens: Number(row.promptTokens ?? 0),
        completionTokens: Number(row.completionTokens ?? 0),
      }));
      const daily = dailyUsageBuckets(tx, projectId, now);
      return {
        projectId,
        requestCount: perModel.reduce((total, entry) => total + entry.requests, 0),
        promptTokens: perModel.reduce((total, entry) => total + entry.promptTokens, 0),
        completionTokens: perModel.reduce((total, entry) => total + entry.completionTokens, 0),
        perModel,
        daily,
      };
    });
  }

  findJob(scope: ProjectScope, projectId: string, jobId: string): JobRecord {
    return this.db.transaction((tx) => {
      const project: ProjectRow = scopedProject(tx, scope, projectId);
      const job = this.scopedJob(tx, project.id, jobId);
      return jobWithEvents(tx, job.id);
    });
  }

  /** The audit index: newest summaries first, with complete bodies read separately. */
  collectProjectJobSummaries(
    scope: ProjectScope,
    projectId: string,
    input: JobPageInput,
  ): JobSummaryPage {
    const limit = jobPageLimit(input.limit);
    return this.db.transaction((tx) => {
      const project: ProjectRow = scopedProject(tx, scope, projectId);
      const rows = buildProjectJobSummariesQuery(tx, project.id, { ...input, limit }).all();
      const returnedRows = rows.slice(0, limit);
      if (returnedRows.length === 0) {
        return { jobs: [], nextCursor: null };
      }
      const boundary = returnedRows.at(-1);
      const nextCursor =
        rows.length > limit && boundary !== undefined
          ? { createdAtMs: boundary.createdAt.getTime(), id: boundary.id }
          : null;
      return { jobs: returnedRows, nextCursor };
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
      this.assertOpenTransition(tx, projectId, jobId, input.status);
      applyJobOutcome(tx, jobId, input);
      return jobWithEvents(tx, jobId);
    });
  }

  /**
   * #392: a terminal outcome may only land on a job that is still open
   * (`running` or `pending`). Anything else is a pipeline protocol error,
   * not a silent overwrite of an already-terminal job. Test seams write
   * states directly through the database and bypass this assertion.
   */
  private assertOpenTransition(
    tx: Tx,
    projectId: string,
    jobId: string,
    attemptedStatus: string,
  ): void {
    const job = this.scopedJob(tx, projectId, jobId);
    if (job.status !== "running" && job.status !== "pending") {
      throw new InvalidJobTransitionError(jobId, job.status, attemptedStatus);
    }
  }

  /** One job lookup guarded by the already-verified project scope. */
  private scopedJob(tx: Tx, projectId: string, jobId: string): JobRow {
    const job = tx.select().from(jobs).where(eq(jobs.id, jobId)).get();
    if (job === undefined || job.project_id !== projectId) {
      throw new NotFoundError("Job not found.");
    }
    return job;
  }

  /**
   * The usage-ledger write inside an open transaction. A protected seam so
   * tests can inject a failure between the job and usage writes and prove
   * the enclosing transaction rolls both back (#392).
   */
  protected writeUsageEvent(tx: Tx, input: AddUsageEventInput): void {
    writeUsageEventRow(tx, input);
  }
}
