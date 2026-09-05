import { eq } from "drizzle-orm";

import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import { jobs } from "../../../shared/infrastructure/db/schema.js";
import type { AddJobInput } from "../application/ports/job_records.js";
import type {
  EvaluatedReview,
  ReviewCompletionRecord,
  ReviewOutcomeStore,
  ReviewSource,
} from "../application/ports/review_outcome_store.js";
import type { ProjectScope } from "../application/ports/studio_store.js";
import { InvalidJobTransitionError, NotFoundError } from "../domain/exceptions.js";
import { applyJobOutcome, insertJobAndEvent } from "./db/job_writes.js";
import {
  loadProjectReviewAssessments,
  persistReviewAssessment,
  readReviewSourceDocuments,
} from "./db/review_records.js";
import { scopedProject, type Tx } from "./db/studio_query_helpers.js";
import { jobWithEvents } from "./job_store_part.js";

/** Atomic persistence adapter for source reads and successful review outcomes. */
export class ReviewStorePart implements ReviewOutcomeStore {
  constructor(protected readonly db: StudioSqliteDatabase) {}

  readReviewSource(scope: ProjectScope, projectId: string, capturedAt: Date): ReviewSource {
    return this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      return {
        projectId: project.id,
        capturedAt,
        documents: readReviewSourceDocuments(tx, project.id),
      };
    });
  }

  recordCompletedReviewJob(scope: ProjectScope, input: EvaluatedReview): ReviewCompletionRecord {
    return this.db.transaction(
      (tx) => {
        scopedProject(tx, scope, input.source.projectId);
        const assessment = persistReviewAssessment(tx, input.source.projectId, input, (reviewId) =>
          this.beforeReviewInsert(tx, reviewId),
        );
        const jobId = this.insertFreshCompletedJob(tx, completedReviewJobInput(input, assessment));
        return { assessment, job: jobWithEvents(tx, jobId) };
      },
      { behavior: "immediate" },
    );
  }

  completeReviewRetryJob(
    scope: ProjectScope,
    projectId: string,
    jobId: string,
    input: EvaluatedReview,
  ): ReviewCompletionRecord {
    return this.db.transaction(
      (tx) => {
        scopedProject(tx, scope, projectId);
        const job = tx.select().from(jobs).where(eq(jobs.id, jobId)).get();
        if (
          job === undefined ||
          job.project_id !== projectId ||
          job.kind !== "review" ||
          job.operation !== "review" ||
          job.document_id !== null ||
          job.retry_of_job_id === null
        ) {
          throw new NotFoundError("Review retry job not found.");
        }
        if (job.status !== "running" && job.status !== "pending") {
          throw new InvalidJobTransitionError(job.id, job.status, "completed");
        }
        if (job.provider !== input.provider) {
          throw new Error("Review evaluation provider does not match the retry job.");
        }
        const assessment = persistReviewAssessment(tx, projectId, input, (reviewId) =>
          this.beforeReviewInsert(tx, reviewId),
        );
        this.applyRetryCompletion(tx, job.id, input, assessment);
        return { assessment, job: jobWithEvents(tx, job.id) };
      },
      { behavior: "immediate" },
    );
  }

  listEditorialAssessments(scope: ProjectScope, projectId: string) {
    return this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      return loadProjectReviewAssessments(tx, project.id);
    });
  }

  /** Failure-injection seam: a throw must roll back review evidence too. */
  protected insertFreshCompletedJob(tx: Tx, input: AddJobInput): string {
    return insertJobAndEvent(tx, input, (jobId) => this.beforeFreshJobEventInsert(tx, jobId));
  }

  /** Failure-injection seam after snapshot rows but before the review row. */
  protected beforeReviewInsert(_tx: Tx, _reviewId: string): void {}

  /** Failure-injection seam after the fresh job row but before its event. */
  protected beforeFreshJobEventInsert(_tx: Tx, _jobId: string): void {}

  /** Failure-injection seam after retry update but before its completed event. */
  protected beforeRetryEventInsert(_tx: Tx, _jobId: string): void {}

  /** Failure-injection seam: a throw must leave the retry running and evidence absent. */
  protected applyRetryCompletion(
    tx: Tx,
    jobId: string,
    input: EvaluatedReview,
    assessment: ReviewCompletionRecord["assessment"],
  ): void {
    applyJobOutcome(
      tx,
      jobId,
      {
        status: "completed",
        model: input.model,
        resultJson: reviewResultJson(assessment),
        error: null,
        eventDetailsJson: JSON.stringify({ review_id: assessment.id }),
        now: input.completedAt,
      },
      (completedJobId) => this.beforeRetryEventInsert(tx, completedJobId),
    );
  }
}

function completedReviewJobInput(
  input: EvaluatedReview,
  assessment: ReviewCompletionRecord["assessment"],
): AddJobInput {
  return {
    projectId: input.source.projectId,
    documentId: null,
    kind: "review",
    operation: "review",
    status: "completed",
    provider: input.provider,
    model: input.model,
    requestJson: JSON.stringify({}),
    resultJson: reviewResultJson(assessment),
    error: null,
    eventDetailsJson: JSON.stringify({ review_id: assessment.id }),
    now: input.completedAt,
  };
}

function reviewResultJson(assessment: ReviewCompletionRecord["assessment"]): string {
  return JSON.stringify({
    review_id: assessment.id,
    snapshot_id: assessment.snapshotId,
    summary: assessment.summary,
  });
}
