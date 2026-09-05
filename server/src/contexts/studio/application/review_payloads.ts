import type {
  ReviewPayload,
  ReviewSeverity,
  ReviewSummaryPayload,
} from "./payload_schemas/review.js";
import { dumpJson } from "./payloads.js";
import type { ReviewSummaryRecord } from "./ports/review_outcome_store.js";
import type { EditorialAssessment } from "./review_service.js";

/**
 * Review payload builders split from `payloads.ts` when the shared module
 * crossed the file-size budget (#459 rebase onto #473/#474). Builders and
 * the TypeBox payload SSOT stay one shape by construction (#433, #440).
 */

/** The review-job result payload shared by the bridge and the retry path. */
export function reviewJobResultJson(assessment: {
  id: string;
  snapshotId: string;
  summary: string;
}): string {
  return dumpJson({
    review_id: assessment.id,
    snapshot_id: assessment.snapshotId,
    summary: assessment.summary,
  });
}

/**
 * One stored editorial assessment for the review DETAIL surface (#459);
 * identical to the shape the review bridge lands in the job `result` JSON.
 */
export function reviewPayload(assessment: EditorialAssessment): ReviewPayload {
  return {
    id: assessment.id,
    project_id: assessment.projectId,
    snapshot_id: assessment.snapshotId,
    provider: assessment.provider,
    model: assessment.model,
    summary: assessment.summary,
    created_at: assessment.createdAt.toISOString(),
    issues: assessment.issues.map((issue) => ({
      id: issue.id,
      document_id: issue.documentId,
      // Store rows carry write-coerced severities; the payload declares the
      // closed read-compatible set from the review SSOT.
      severity: issue.severity as ReviewSeverity,
      code: issue.code,
      message: issue.message,
      suggestion: issue.suggestion,
      evidence: { ...issue.evidence },
    })),
  };
}

/** One bounded review-history summary for the review LIST surface (#459). */
export function reviewSummaryPayload(summary: ReviewSummaryRecord): ReviewSummaryPayload {
  return {
    id: summary.id,
    project_id: summary.projectId,
    snapshot_id: summary.snapshotId,
    provider: summary.provider,
    model: summary.model,
    summary: summary.summary,
    issue_count: summary.issueCount,
    created_at: summary.createdAt.toISOString(),
  };
}
