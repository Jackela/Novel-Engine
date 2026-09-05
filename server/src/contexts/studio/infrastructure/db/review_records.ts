import { randomUUID } from "node:crypto";
import { and, asc, desc, eq, inArray } from "drizzle-orm";

import { InvalidOperationError } from "../../../../shared/domain/exceptions.js";
import type {
  EditorialAssessmentRecord,
  EditorialIssueInput,
  EditorialIssueRecord,
  EvaluatedReview,
  ReviewSnapshotDocument,
  ReviewSourceDocument,
} from "../../application/ports/review_outcome_store.js";
import { ReviewSourceInvalidatedError } from "../../domain/exceptions.js";
import {
  documentRevisions,
  documents,
  projectSnapshots,
  reviewIssues,
  reviews,
  snapshotDocuments,
  volumes,
} from "./schema.js";
import { compareReadingOrder, type Tx } from "./studio_query_helpers.js";

type ReviewRow = typeof reviews.$inferSelect;
type ReviewIssueRow = typeof reviewIssues.$inferSelect;

/** Read the current revision set without creating durable snapshot rows. */
export function readReviewSourceDocuments(tx: Tx, projectId: string): ReviewSourceDocument[] {
  const rows = tx
    .select({ document: documents, revision: documentRevisions, volumePosition: volumes.position })
    .from(documents)
    .innerJoin(documentRevisions, eq(documents.currentRevisionId, documentRevisions.id))
    .leftJoin(volumes, eq(documents.volumeId, volumes.id))
    .where(eq(documents.projectId, projectId))
    .all();
  return rows
    .map((row) => ({
      key: {
        kind: row.document.kind,
        position: row.document.position,
        createdAt: row.document.createdAt,
        id: row.document.id,
        volumePosition: row.volumePosition ?? null,
      },
      row,
    }))
    .sort((left, right) => compareReadingOrder(left.key, right.key))
    .map(({ row: { document, revision } }, index) => ({
      documentId: document.id,
      revisionId: revision.id,
      kind: document.kind,
      title: document.title,
      contentMarkdown: revision.contentMarkdown,
      metadataJson: revision.metadataJson,
      position: index + 1,
    }));
}

/** Persist one valid evaluation inside its caller-owned transaction. */
export function persistReviewAssessment(
  tx: Tx,
  projectId: string,
  input: EvaluatedReview,
  beforeReviewInsert: (reviewId: string) => void = () => {},
): EditorialAssessmentRecord {
  if (input.source.projectId !== projectId) {
    throw new Error("Review source project does not match the persistence target.");
  }
  assertReviewSourceAvailable(tx, projectId, input.source.documents);
  const snapshotId = randomUUID();
  tx.insert(projectSnapshots)
    .values({
      id: snapshotId,
      projectId,
      reason: "review",
      createdAt: input.source.capturedAt,
    })
    .run();
  const captured = persistSnapshotDocuments(tx, snapshotId, input.source.documents);
  const review: ReviewRow = {
    id: randomUUID(),
    projectId,
    snapshotId,
    provider: input.provider,
    model: input.model,
    summary: input.summary,
    createdAt: input.completedAt,
  };
  beforeReviewInsert(review.id);
  tx.insert(reviews).values(review).run();
  const issues = persistFindings(tx, review.id, input.issues, captured);
  return toEditorialAssessment(review, issues);
}

/** Load persisted assessments newest first for the read surface. */
export function loadProjectReviewAssessments(
  tx: Tx,
  projectId: string,
): EditorialAssessmentRecord[] {
  return tx
    .select()
    .from(reviews)
    .where(eq(reviews.projectId, projectId))
    .orderBy(desc(reviews.createdAt), desc(reviews.id))
    .all()
    .map((review) => toEditorialAssessment(review, findReviewIssues(tx, review.id)));
}

function assertReviewSourceAvailable(
  tx: Tx,
  projectId: string,
  source: readonly ReviewSourceDocument[],
): void {
  if (source.length === 0) return;
  const revisionIds = source.map((document) => document.revisionId);
  const rows = tx
    .select({
      documentId: documents.id,
      revisionId: documentRevisions.id,
      contentMarkdown: documentRevisions.contentMarkdown,
      metadataJson: documentRevisions.metadataJson,
    })
    .from(documents)
    .innerJoin(documentRevisions, eq(documentRevisions.documentId, documents.id))
    .where(and(eq(documents.projectId, projectId), inArray(documentRevisions.id, revisionIds)))
    .all();
  const available = new Map(rows.map((row) => [`${row.documentId}\u0000${row.revisionId}`, row]));
  for (const document of source) {
    const row = available.get(`${document.documentId}\u0000${document.revisionId}`);
    if (row === undefined) throw new ReviewSourceInvalidatedError();
    if (
      row.contentMarkdown !== document.contentMarkdown ||
      row.metadataJson !== document.metadataJson
    ) {
      throw new Error("Persisted immutable review source changed after capture.");
    }
  }
}

function persistSnapshotDocuments(
  tx: Tx,
  snapshotId: string,
  source: readonly ReviewSourceDocument[],
): ReviewSnapshotDocument[] {
  return source.map((document) => {
    const captured: ReviewSnapshotDocument = {
      ...document,
      snapshotDocumentId: randomUUID(),
    };
    tx.insert(snapshotDocuments)
      .values({
        id: captured.snapshotDocumentId,
        snapshotId,
        documentId: captured.documentId,
        revisionId: captured.revisionId,
        documentKind: captured.kind,
        documentTitle: captured.title,
        revisionMetadataJson: captured.metadataJson,
        position: captured.position,
      })
      .run();
    return captured;
  });
}

function loadSnapshotDocuments(tx: Tx, snapshotId: string): ReviewSnapshotDocument[] {
  return tx
    .select({ snapshotDocument: snapshotDocuments, revision: documentRevisions })
    .from(snapshotDocuments)
    .innerJoin(documentRevisions, eq(snapshotDocuments.revisionId, documentRevisions.id))
    .where(eq(snapshotDocuments.snapshotId, snapshotId))
    .orderBy(asc(snapshotDocuments.position), asc(snapshotDocuments.id))
    .all()
    .map(({ snapshotDocument, revision }) => ({
      documentId: snapshotDocument.documentId,
      snapshotDocumentId: snapshotDocument.id,
      revisionId: snapshotDocument.revisionId,
      kind: snapshotDocument.documentKind,
      title: snapshotDocument.documentTitle,
      contentMarkdown: revision.contentMarkdown,
      metadataJson: snapshotDocument.revisionMetadataJson,
      position: snapshotDocument.position,
    }));
}

function persistFindings(
  tx: Tx,
  reviewId: string,
  findings: readonly EditorialIssueInput[],
  captured: readonly ReviewSnapshotDocument[],
): EditorialIssueRecord[] {
  const byDocumentId = new Map(captured.map((document) => [document.documentId, document]));
  const rows = findings.map((finding) => {
    const document = byDocumentId.get(finding.documentId);
    if (document === undefined) {
      throw new InvalidOperationError(
        "Review finding refers to a document outside the captured snapshot.",
      );
    }
    const issue: ReviewIssueRow = {
      id: randomUUID(),
      reviewId,
      snapshotDocumentId: document.snapshotDocumentId,
      documentId: document.documentId,
      severity: finding.severity,
      code: finding.code,
      message: finding.message,
      suggestion: finding.suggestion,
      evidenceJson: serializeEvidence(finding.evidence),
    };
    return issue;
  });
  if (rows.length > 0) tx.insert(reviewIssues).values(rows).run();
  return orderedIssues(rows.map(toEditorialIssue), captured);
}

function findReviewIssues(tx: Tx, reviewId: string): EditorialIssueRecord[] {
  const review = tx.select().from(reviews).where(eq(reviews.id, reviewId)).get();
  if (review === undefined) return [];
  const captured = loadSnapshotDocuments(tx, review.snapshotId);
  const issues = tx
    .select()
    .from(reviewIssues)
    .where(eq(reviewIssues.reviewId, reviewId))
    .all()
    .map(toEditorialIssue);
  return orderedIssues(issues, captured);
}

function orderedIssues(
  issues: EditorialIssueRecord[],
  captured: readonly ReviewSnapshotDocument[],
): EditorialIssueRecord[] {
  const position = new Map(captured.map((document) => [document.documentId, document.position]));
  return issues.sort(
    (left, right) =>
      left.severity.localeCompare(right.severity) ||
      left.code.localeCompare(right.code) ||
      (position.get(left.documentId) ?? 0) - (position.get(right.documentId) ?? 0),
  );
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
