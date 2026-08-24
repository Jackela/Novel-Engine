import { randomUUID } from "node:crypto";
import { asc, desc, eq } from "drizzle-orm";

import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import type {
  EditorialAssessmentRecord,
  EditorialIssueInput,
  EditorialIssueRecord,
  ProjectScope,
  RecordSnapshotReviewInput,
  ReviewSnapshotDocument,
} from "../application/ports/studio_store.js";
import {
  documentRevisions,
  documents,
  projectSnapshots,
  reviewIssues,
  reviews,
  snapshotDocuments,
} from "./db/schema.js";
import { scopedProject, type Tx } from "./db/studio_query_helpers.js";

type ReviewRow = typeof reviews.$inferSelect;
type ReviewIssueRow = typeof reviewIssues.$inferSelect;

/**
 * Snapshot-bound editorial review persistence. The evaluator is deliberately
 * injected from application code and sees only already-captured content.
 */
export class ReviewStorePart {
  private readonly db: StudioSqliteDatabase;

  constructor(db: StudioSqliteDatabase) {
    this.db = db;
  }

  recordSnapshotReview(
    scope: ProjectScope,
    projectId: string,
    input: RecordSnapshotReviewInput,
  ): EditorialAssessmentRecord {
    return this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      const snapshotId = randomUUID();
      tx.insert(projectSnapshots)
        .values({ id: snapshotId, projectId: project.id, reason: "review", createdAt: input.now })
        .run();
      const captured = captureReviewSnapshot(tx, project.id, snapshotId);
      const findings = input.evaluator(captured);
      const review: ReviewRow = {
        id: randomUUID(),
        projectId: project.id,
        snapshotId,
        provider: input.provider,
        model: input.model,
        summary: input.summary,
        createdAt: input.now,
      };
      tx.insert(reviews).values(review).run();
      const issues = persistFindings(tx, review.id, findings, captured);
      return toEditorialAssessment(review, issues);
    });
  }

  listEditorialAssessments(scope: ProjectScope, projectId: string): EditorialAssessmentRecord[] {
    return this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      return tx
        .select()
        .from(reviews)
        .where(eq(reviews.projectId, project.id))
        .orderBy(desc(reviews.createdAt), desc(reviews.id))
        .all()
        .map((review) => toEditorialAssessment(review, findReviewIssues(tx, review.id)));
    });
  }
}

function captureReviewSnapshot(
  tx: Tx,
  projectId: string,
  snapshotId: string,
): ReviewSnapshotDocument[] {
  const rows = tx
    .select({ document: documents, revision: documentRevisions })
    .from(documents)
    .innerJoin(documentRevisions, eq(documents.currentRevisionId, documentRevisions.id))
    .where(eq(documents.projectId, projectId))
    .orderBy(asc(documents.position), asc(documents.createdAt), asc(documents.id))
    .all();
  return rows.map(({ document, revision }) => {
    const snapshotDocument: ReviewSnapshotDocument = {
      documentId: document.id,
      snapshotDocumentId: randomUUID(),
      revisionId: revision.id,
      kind: document.kind,
      title: document.title,
      contentMarkdown: revision.contentMarkdown,
      metadataJson: revision.metadataJson,
      position: document.position,
    };
    tx.insert(snapshotDocuments)
      .values({
        id: snapshotDocument.snapshotDocumentId,
        snapshotId,
        documentId: snapshotDocument.documentId,
        revisionId: snapshotDocument.revisionId,
        documentKind: snapshotDocument.kind,
        documentTitle: snapshotDocument.title,
        revisionMetadataJson: snapshotDocument.metadataJson,
        position: snapshotDocument.position,
      })
      .run();
    return snapshotDocument;
  });
}

function persistFindings(
  tx: Tx,
  reviewId: string,
  findings: readonly EditorialIssueInput[],
  captured: readonly ReviewSnapshotDocument[],
): EditorialIssueRecord[] {
  const byDocumentId = new Map(captured.map((document) => [document.documentId, document]));
  const rows = findings.map((finding) => {
    const snapshotDocument = byDocumentId.get(finding.documentId);
    if (snapshotDocument === undefined) {
      throw new InvalidOperationError(
        "Review finding refers to a document outside the captured snapshot.",
      );
    }
    const issue: ReviewIssueRow = {
      id: randomUUID(),
      reviewId,
      snapshotDocumentId: snapshotDocument.snapshotDocumentId,
      documentId: snapshotDocument.documentId,
      severity: finding.severity,
      code: finding.code,
      message: finding.message,
      suggestion: finding.suggestion,
      evidenceJson: serializeEvidence(finding.evidence),
    };
    return issue;
  });
  if (rows.length > 0) {
    tx.insert(reviewIssues).values(rows).run();
  }
  return rows.map(toEditorialIssue).sort(compareEditorialIssues);
}

function findReviewIssues(tx: Tx, reviewId: string): EditorialIssueRecord[] {
  return tx
    .select()
    .from(reviewIssues)
    .where(eq(reviewIssues.reviewId, reviewId))
    .orderBy(asc(reviewIssues.severity), asc(reviewIssues.code), asc(reviewIssues.id))
    .all()
    .map(toEditorialIssue);
}

function toEditorialAssessment(
  review: ReviewRow,
  issues: EditorialIssueRecord[],
): EditorialAssessmentRecord {
  return {
    id: review.id,
    projectId: review.projectId,
    snapshotId: review.snapshotId,
    provider: review.provider,
    model: review.model,
    summary: review.summary,
    createdAt: review.createdAt,
    issues,
  };
}

function toEditorialIssue(issue: ReviewIssueRow): EditorialIssueRecord {
  if (issue.documentId === null) {
    throw new InvalidOperationError("Snapshot review issues must retain their source document.");
  }
  return {
    id: issue.id,
    reviewId: issue.reviewId,
    snapshotDocumentId: issue.snapshotDocumentId,
    documentId: issue.documentId,
    severity: issue.severity,
    code: issue.code,
    message: issue.message,
    suggestion: issue.suggestion,
    evidence: parseEvidence(issue.evidenceJson),
  };
}

function serializeEvidence(evidence: Record<string, unknown>): string {
  const serialized = JSON.stringify(evidence);
  if (serialized === undefined) {
    throw new InvalidOperationError("Review issue evidence must be serializable.");
  }
  return serialized;
}

function parseEvidence(serialized: string): Record<string, unknown> {
  const evidence: unknown = JSON.parse(serialized);
  if (evidence === null || Array.isArray(evidence) || typeof evidence !== "object") {
    throw new InvalidOperationError("Review issue evidence must be an object.");
  }
  return evidence as Record<string, unknown>;
}

function compareEditorialIssues(left: EditorialIssueRecord, right: EditorialIssueRecord): number {
  return (
    left.severity.localeCompare(right.severity) ||
    left.code.localeCompare(right.code) ||
    left.id.localeCompare(right.id)
  );
}
