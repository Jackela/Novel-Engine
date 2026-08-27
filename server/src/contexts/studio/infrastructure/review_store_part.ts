import { randomUUID } from "node:crypto";
import { and, asc, desc, eq } from "drizzle-orm";

import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import type {
  CaptureReviewSnapshotInput,
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
  volumes,
} from "./db/schema.js";
import { compareReadingOrder, scopedProject, type Tx } from "./db/studio_query_helpers.js";

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

  captureReviewSnapshot(
    scope: ProjectScope,
    projectId: string,
    input: CaptureReviewSnapshotInput,
  ): { snapshotId: string; documents: ReviewSnapshotDocument[] } {
    return this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      const snapshotId = randomUUID();
      tx.insert(projectSnapshots)
        .values({ id: snapshotId, projectId: project.id, reason: "review", createdAt: input.now })
        .run();
      return { snapshotId, documents: captureReviewSnapshot(tx, project.id, snapshotId) };
    });
  }

  recordSnapshotReview(
    scope: ProjectScope,
    projectId: string,
    input: RecordSnapshotReviewInput,
  ): EditorialAssessmentRecord {
    return this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      const [snapshot] = tx
        .select({ id: projectSnapshots.id })
        .from(projectSnapshots)
        .where(
          and(
            eq(projectSnapshots.id, input.snapshotId),
            eq(projectSnapshots.projectId, project.id),
          ),
        )
        .all();
      if (snapshot === undefined) {
        throw new InvalidOperationError("Review snapshot does not belong to this project.");
      }
      const captured = loadSnapshotDocuments(tx, input.snapshotId);
      const review: ReviewRow = {
        id: randomUUID(),
        projectId: project.id,
        snapshotId: input.snapshotId,
        provider: input.provider,
        model: input.model,
        summary: input.summary,
        createdAt: input.now,
      };
      tx.insert(reviews).values(review).run();
      const issues = persistFindings(tx, review.id, input.issues, captured);
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
    .select({
      document: documents,
      revision: documentRevisions,
      volumePosition: volumes.position,
    })
    .from(documents)
    .innerJoin(documentRevisions, eq(documents.currentRevisionId, documentRevisions.id))
    .leftJoin(volumes, eq(documents.volumeId, volumes.id))
    .where(eq(documents.projectId, projectId))
    .all();
  const ordered = rows
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
    .map((entry) => entry.row);
  return ordered.map(({ document, revision }, index) => {
    const snapshotDocument: ReviewSnapshotDocument = {
      documentId: document.id,
      snapshotDocumentId: randomUUID(),
      revisionId: revision.id,
      kind: document.kind,
      title: document.title,
      contentMarkdown: revision.contentMarkdown,
      metadataJson: revision.metadataJson,
      // Dense reading-order index so review findings sort in reading order.
      position: index + 1,
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

function loadSnapshotDocuments(tx: Tx, snapshotId: string): ReviewSnapshotDocument[] {
  const rows = tx
    .select({
      snapshotDocument: snapshotDocuments,
      revision: documentRevisions,
    })
    .from(snapshotDocuments)
    .innerJoin(documentRevisions, eq(snapshotDocuments.revisionId, documentRevisions.id))
    .where(eq(snapshotDocuments.snapshotId, snapshotId))
    .orderBy(asc(snapshotDocuments.position), asc(snapshotDocuments.id))
    .all();
  return rows.map(({ snapshotDocument, revision }) => ({
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
  const positionByDocument = new Map(
    captured.map((document) => [document.documentId, document.position]),
  );
  return rows
    .map(toEditorialIssue)
    .sort(
      (left, right) =>
        left.severity.localeCompare(right.severity) ||
        left.code.localeCompare(right.code) ||
        (positionByDocument.get(left.documentId) ?? 0) -
          (positionByDocument.get(right.documentId) ?? 0),
    );
}

function findReviewIssues(tx: Tx, reviewId: string): EditorialIssueRecord[] {
  const captured = loadSnapshotDocumentsByReview(tx, reviewId);
  const positionByDocument = new Map(
    captured.map((document) => [document.documentId, document.position]),
  );
  return tx
    .select()
    .from(reviewIssues)
    .where(eq(reviewIssues.reviewId, reviewId))
    .all()
    .map(toEditorialIssue)
    .sort(
      (left, right) =>
        left.severity.localeCompare(right.severity) ||
        left.code.localeCompare(right.code) ||
        (positionByDocument.get(left.documentId) ?? 0) -
          (positionByDocument.get(right.documentId) ?? 0),
    );
}

/** Snapshot documents of one review, reloaded for read-path ordering. */
function loadSnapshotDocumentsByReview(tx: Tx, reviewId: string): ReviewSnapshotDocument[] {
  const [review] = tx.select().from(reviews).where(eq(reviews.id, reviewId)).all();
  if (review === undefined) {
    return [];
  }
  return loadSnapshotDocuments(tx, review.snapshotId);
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
