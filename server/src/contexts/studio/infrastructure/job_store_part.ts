import { asc, eq, sql } from "drizzle-orm";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import { jobs, usageEvents } from "../../../shared/infrastructure/db/schema.js";
import {
  type JobPageInput,
  type JobSummaryPage,
  jobPageLimit,
} from "../application/ports/job_records.js";
import type {
  AddJobInput,
  AddUsageEventInput,
  ClaimJobRetryInput,
  CompleteJobWithUsageInput,
  JobRecord,
  JobRetryClaim,
  MarkJobOutcomeInput,
  ProjectScope,
  ProjectUsageAggregate,
  RecordCompletedProposalJobInput,
} from "../application/ports/studio_store.js";
import {
  InvalidJobTransitionError,
  NotFoundError,
  OperationInFlightError,
} from "../domain/exceptions.js";
import { jobWithEvents } from "./db/job_record_reads.js";
import { findRetryJobByKey, insertRetryClaim } from "./db/job_retry_claim.js";
import {
  applyJobOutcome,
  insertJobAndEvent,
  writeUsageEvent as writeUsageEventRow,
} from "./db/job_writes.js";
import { addSafeUsage, safeUsageAggregate } from "./db/safe_usage_tokens.js";
import { type ProjectRow, scopedProject, type Tx } from "./db/studio_query_helpers.js";
import { dailyUsageBuckets } from "./db/usage_daily_buckets.js";
import { buildProjectJobSummariesQuery } from "./job_page_queries.js";

export { jobWithEvents };

type JobRow = typeof jobs.$inferSelect;
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

  findJobRetry(
    scope: ProjectScope,
    projectId: string,
    sourceJobId: string,
    requestKey: string,
  ): JobRecord | null {
    return this.db.transaction((tx) => {
      scopedProject(tx, scope, projectId);
      const retry = findRetryJobByKey(tx, projectId, sourceJobId, requestKey);
      return retry === undefined ? null : jobWithEvents(tx, retry.id);
    });
  }

  claimJobRetry(scope: ProjectScope, input: ClaimJobRetryInput): JobRetryClaim {
    return this.db.transaction(
      (tx) => {
        scopedProject(tx, scope, input.projectId);
        const existing = findRetryJobByKey(
          tx,
          input.projectId,
          input.sourceJobId,
          input.requestKey,
        );
        if (existing !== undefined) return this.replayRetryClaim(tx, existing);

        const source = this.scopedJob(tx, input.projectId, input.sourceJobId);
        this.assertRetryableSource(source);
        const claimed = insertRetryClaim(tx, source, input.requestKey, input.now, (jobId) =>
          this.beforeRetryClaimEventInsert(tx, jobId),
        );
        if (claimed.created) return { job: jobWithEvents(tx, claimed.jobId), created: true };
        const winner = findRetryJobByKey(tx, input.projectId, input.sourceJobId, input.requestKey);
        if (winner === undefined) throw new Error("Retry idempotency winner disappeared.");
        return this.replayRetryClaim(tx, winner);
      },
      { behavior: "immediate" },
    );
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
          requests: sql<string>`CAST(COUNT(*) AS TEXT)`,
          promptTokens: sql<string>`CAST(SUM(${usageEvents.prompt_tokens}) AS TEXT)`,
          completionTokens: sql<string>`CAST(SUM(${usageEvents.completion_tokens}) AS TEXT)`,
        })
        .from(usageEvents)
        .where(eq(usageEvents.project_id, projectId))
        .groupBy(usageEvents.model)
        .orderBy(asc(usageEvents.model))
        .all();
      const perModel = rows.map((row) => ({
        model: row.model,
        requests: safeUsageAggregate(row.requests, "request"),
        promptTokens: safeUsageAggregate(row.promptTokens, "prompt"),
        completionTokens: safeUsageAggregate(row.completionTokens, "completion"),
      }));
      const daily = dailyUsageBuckets(tx, projectId, now);
      return {
        projectId,
        requestCount: perModel.reduce(
          (total, entry) => addSafeUsage(total, entry.requests, "request"),
          0,
        ),
        promptTokens: perModel.reduce(
          (total, entry) => addSafeUsage(total, entry.promptTokens, "prompt"),
          0,
        ),
        completionTokens: perModel.reduce(
          (total, entry) => addSafeUsage(total, entry.completionTokens, "completion"),
          0,
        ),
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

  /** Failure-injection seam proving the retry row and first event stay atomic. */
  protected beforeRetryClaimEventInsert(_tx: Tx, _jobId: string): void {}

  private replayRetryClaim(tx: Tx, retry: JobRow): JobRetryClaim {
    if (retry.status === "running") {
      throw new OperationInFlightError(
        retry.project_id,
        null,
        `retry (${String(retry.retry_of_job_id)})`,
        1,
      );
    }
    if (
      retry.status !== "completed" &&
      retry.status !== "failed" &&
      retry.status !== "interrupted"
    ) {
      throw new Error(`Persisted retry Job has invalid status: ${retry.status}.`);
    }
    return { job: jobWithEvents(tx, retry.id), created: false };
  }

  private assertRetryableSource(source: JobRow): void {
    if (source.status !== "failed" && source.status !== "interrupted") {
      throw new InvalidOperationError("Only failed or interrupted jobs may be retried.");
    }
    if (source.kind === "import") {
      throw new InvalidOperationError("Import jobs cannot be retried.");
    }
    if (source.kind !== "proposal" && source.kind !== "review" && source.kind !== "export") {
      throw new InvalidOperationError(`Unsupported job kind for retry: ${source.kind}`);
    }
  }
}
