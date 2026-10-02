import type { JobRecord } from "./job_records.js";
import { pageLimit } from "./page_limit.js";
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
  /**
   * The project's stored provider selection (DR-024), read in the same
   * transaction as the documents so review and generation follow one
   * author-visible choice. It is the raw settings value: an empty string
   * means the stored settings name no provider, and the application falls
   * back to its server-level default instead of failing the read.
   */
  readonly provider: string;
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

/** Lightweight review-history item; complete ordered issues live on the detail read. */
export interface ReviewSummaryRecord {
  readonly id: string;
  readonly projectId: string;
  readonly snapshotId: string;
  readonly provider: string;
  readonly model: string;
  readonly summary: string;
  readonly issueCount: number;
  readonly createdAt: Date;
}

/** The validated row budget of one bounded review-history page. */
export type ReviewPageLimit = number & { readonly __reviewPageLimit: unique symbol };

/** Inclusive application/store boundary for one page of review history. */
const MIN_REVIEW_PAGE_LIMIT = 1;
const MAX_REVIEW_PAGE_LIMIT = 100;

/** Validate and narrow a transport/application number before it reaches persistence. */
export function reviewPageLimit(value: number): ReviewPageLimit {
  return pageLimit<ReviewPageLimit>(value, {
    min: MIN_REVIEW_PAGE_LIMIT,
    max: MAX_REVIEW_PAGE_LIMIT,
    subject: "Review",
  });
}

/** Persistence-neutral exclusive position in `(created_at DESC, id DESC)` order. */
export interface ReviewPageCursor {
  readonly createdAtMs: number;
  readonly id: string;
}

/** One typed keyset request; the first page omits its exclusive cursor. */
export interface ReviewPageInput {
  readonly limit: ReviewPageLimit;
  readonly cursor?: ReviewPageCursor | undefined;
}

/** One bounded page and the exclusive position required to continue it. */
export interface ReviewSummaryPage {
  readonly reviews: ReviewSummaryRecord[];
  readonly nextCursor: ReviewPageCursor | null;
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

/** One completed review outcome returned from its atomic database command. */
export interface ReviewCompletionRecord {
  readonly assessment: EditorialAssessmentRecord;
  readonly job: JobRecord;
}

/**
 * Deep review-outcome boundary. Provider work sees a read-only source; only a
 * valid result can atomically create immutable evidence and a completed job.
 */
export interface ReviewOutcomeStore {
  /**
   * The project's stored provider selection without reading its manuscript
   * (DR-024): the failure path labels a review job with the provider the
   * attempt actually used, so a retry never silently changes provider.
   */
  readProjectProvider(scope: ProjectScope, projectId: string): string;
  readReviewSource(scope: ProjectScope, projectId: string, capturedAt: Date): ReviewSource;
  recordCompletedReviewJob(scope: ProjectScope, input: EvaluatedReview): ReviewCompletionRecord;
  completeReviewRetryJob(
    scope: ProjectScope,
    projectId: string,
    jobId: string,
    input: EvaluatedReview,
  ): ReviewCompletionRecord;
  collectProjectReviewSummaries(
    scope: ProjectScope,
    projectId: string,
    input: ReviewPageInput,
  ): ReviewSummaryPage;
  findProjectReview(
    scope: ProjectScope,
    projectId: string,
    reviewId: string,
  ): EditorialAssessmentRecord;
}
