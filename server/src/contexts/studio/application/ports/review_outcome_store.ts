import type { JobRecord } from "./job_records.js";
import type { ProjectScope } from "./studio_store.js";

/** A document/revision pair read for provider evaluation without persistence. */
export interface ReviewSourceDocument {
  readonly documentId: string;
  readonly revisionId: string;
  readonly kind: string;
  readonly title: string;
  readonly contentMarkdown: string;
  readonly metadataJson: string;
  readonly position: number;
}

/** The ordered point-in-time source evaluated by one review request. */
export interface ReviewSource {
  readonly projectId: string;
  readonly capturedAt: Date;
  readonly documents: readonly ReviewSourceDocument[];
}

/** A source document after it has been bound to a durable snapshot row. */
export interface ReviewSnapshotDocument extends ReviewSourceDocument {
  readonly snapshotDocumentId: string;
}

/** A pure evaluator's finding, before the adapter serializes its evidence. */
export interface EditorialIssueInput {
  readonly documentId: string;
  readonly severity: string;
  readonly code: string;
  readonly message: string;
  readonly suggestion: string;
  readonly evidence: Record<string, unknown>;
}

/** One persisted editorial issue, returned without exposing database rows. */
export interface EditorialIssueRecord extends EditorialIssueInput {
  readonly id: string;
  readonly reviewId: string;
  readonly snapshotDocumentId: string;
}

/** A snapshot-bound editorial assessment and its stably ordered issues. */
export interface EditorialAssessmentRecord {
  readonly id: string;
  readonly projectId: string;
  readonly snapshotId: string;
  readonly provider: string;
  readonly model: string;
  readonly summary: string;
  readonly createdAt: Date;
  readonly issues: EditorialIssueRecord[];
}

/** Valid provider output ready for one all-or-nothing persistence command. */
export interface EvaluatedReview {
  readonly source: ReviewSource;
  readonly provider: string;
  readonly model: string;
  readonly summary: string;
  readonly completedAt: Date;
  readonly issues: readonly EditorialIssueInput[];
}

export interface ReviewCompletionRecord {
  readonly assessment: EditorialAssessmentRecord;
  readonly job: JobRecord;
}

/**
 * Deep review-outcome boundary. Provider work sees a read-only source; only a
 * valid result can atomically create immutable evidence and a completed job.
 */
export interface ReviewOutcomeStore {
  readReviewSource(scope: ProjectScope, projectId: string, capturedAt: Date): ReviewSource;
  recordCompletedReviewJob(scope: ProjectScope, input: EvaluatedReview): ReviewCompletionRecord;
  completeReviewRetryJob(
    scope: ProjectScope,
    projectId: string,
    jobId: string,
    input: EvaluatedReview,
  ): ReviewCompletionRecord;
  listEditorialAssessments(scope: ProjectScope, projectId: string): EditorialAssessmentRecord[];
}
