import { and, count, eq, sql } from "drizzle-orm";

import { EXPORT_CAPACITY_LIMITS, ExportCapacityExceededError } from "../../domain/exceptions.js";
import {
  documentRevisions,
  documents,
  projectSnapshots,
  projects,
  snapshotDocuments,
} from "./schema.js";
import type { Tx } from "./studio_query_helpers.js";

interface SourceByteMeasure {
  readonly documentBytes: number | null;
  readonly joinedDocuments: number;
  readonly projectTitleBytes: number;
}

/** Reject an oversized live projection before its complete rows enter JavaScript. */
export function assertCurrentExportSourceCapacity(tx: Tx, projectId: string): void {
  const documentCount = currentDocumentCount(tx, projectId);
  assertSourceLimit("source_documents", documentCount);
  const measured = measureCurrentSourceBytes(tx, projectId);
  if (measured.joinedDocuments !== documentCount) {
    throw new Error("Every export source document requires a current revision.");
  }
  const documentBytes = documentCount === 0 ? 0 : measured.documentBytes;
  if (documentBytes === null) {
    throw new Error("Export source byte measurement requires complete revisions.");
  }
  assertSourceLimit("source_bytes", measured.projectTitleBytes + documentBytes);
}

/** Avoid materializing a historical projection that cannot equal a bounded live source. */
export function isExportSnapshotWithinSourceCapacity(
  tx: Tx,
  projectId: string,
  snapshotId: string,
): boolean {
  const documentCount = snapshotDocumentCount(tx, projectId, snapshotId);
  if (documentCount > EXPORT_CAPACITY_LIMITS.source_documents) return false;
  const measured = measureSnapshotSourceBytes(tx, projectId, snapshotId);
  if (measured.joinedDocuments !== documentCount) {
    throw new Error("Export snapshot references an invalid document revision.");
  }
  const documentBytes = documentCount === 0 ? 0 : measured.documentBytes;
  if (documentBytes === null) {
    throw new Error("Export snapshot byte measurement requires complete revisions.");
  }
  return measured.projectTitleBytes + documentBytes <= EXPORT_CAPACITY_LIMITS.source_bytes;
}

function currentDocumentCount(tx: Tx, projectId: string): number {
  const row = buildBoundedCurrentDocumentCountQuery(tx, projectId).get();
  if (row === undefined) throw new Error("Export source count query returned no result.");
  return row.value;
}

export function buildBoundedCurrentDocumentCountQuery(tx: Tx, projectId: string) {
  const bounded = tx
    .select({ id: documents.id })
    .from(documents)
    .where(eq(documents.projectId, projectId))
    .limit(EXPORT_CAPACITY_LIMITS.source_documents + 1)
    .as("bounded_export_source_documents");
  return tx.select({ value: count() }).from(bounded);
}

function measureCurrentSourceBytes(tx: Tx, projectId: string): SourceByteMeasure {
  const row = tx
    .select({
      documentBytes: sql<number | null>`sum(
        octet_length(${documents.id}) +
        octet_length(${documentRevisions.id}) +
        octet_length(${documents.kind}) +
        octet_length(${documents.title}) +
        octet_length(${documentRevisions.contentMarkdown}) +
        octet_length(${documentRevisions.metadataJson})
      )`,
      joinedDocuments: count(documentRevisions.id),
      projectTitleBytes: sql<number>`octet_length(${projects.title})`,
    })
    .from(projects)
    .leftJoin(documents, eq(documents.projectId, projects.id))
    .leftJoin(
      documentRevisions,
      and(
        eq(documents.currentRevisionId, documentRevisions.id),
        eq(documentRevisions.documentId, documents.id),
      ),
    )
    .where(eq(projects.id, projectId))
    .groupBy(projects.id)
    .get();
  if (row === undefined) throw new Error("Export source byte query returned no result.");
  return row;
}

function snapshotDocumentCount(tx: Tx, projectId: string, snapshotId: string): number {
  const row = buildBoundedSnapshotDocumentCountQuery(tx, projectId, snapshotId).get();
  if (row === undefined) throw new Error("Export snapshot count query returned no result.");
  return row.value;
}

export function buildBoundedSnapshotDocumentCountQuery(
  tx: Tx,
  projectId: string,
  snapshotId: string,
) {
  const bounded = tx
    .select({ id: snapshotDocuments.id })
    .from(snapshotDocuments)
    .innerJoin(projectSnapshots, eq(snapshotDocuments.snapshotId, projectSnapshots.id))
    .where(and(eq(projectSnapshots.id, snapshotId), eq(projectSnapshots.projectId, projectId)))
    .limit(EXPORT_CAPACITY_LIMITS.source_documents + 1)
    .as("bounded_export_snapshot_documents");
  return tx.select({ value: count() }).from(bounded);
}

function measureSnapshotSourceBytes(
  tx: Tx,
  projectId: string,
  snapshotId: string,
): SourceByteMeasure {
  const row = tx
    .select({
      documentBytes: sql<number | null>`sum(
        octet_length(${snapshotDocuments.documentId}) +
        octet_length(${snapshotDocuments.revisionId}) +
        octet_length(${snapshotDocuments.documentKind}) +
        octet_length(${snapshotDocuments.documentTitle}) +
        octet_length(${documentRevisions.contentMarkdown}) +
        octet_length(${snapshotDocuments.revisionMetadataJson})
      )`,
      joinedDocuments: count(documentRevisions.id),
      projectTitleBytes: sql<number>`octet_length(${projects.title})`,
    })
    .from(projectSnapshots)
    .innerJoin(projects, eq(projectSnapshots.projectId, projects.id))
    .leftJoin(snapshotDocuments, eq(snapshotDocuments.snapshotId, projectSnapshots.id))
    .leftJoin(
      documentRevisions,
      and(
        eq(snapshotDocuments.revisionId, documentRevisions.id),
        eq(documentRevisions.documentId, snapshotDocuments.documentId),
      ),
    )
    .where(and(eq(projectSnapshots.id, snapshotId), eq(projectSnapshots.projectId, projectId)))
    .groupBy(projectSnapshots.id)
    .get();
  if (row === undefined) throw new Error("Export snapshot byte query returned no result.");
  return row;
}

function assertSourceLimit(resource: "source_documents" | "source_bytes", observed: number): void {
  const limit = EXPORT_CAPACITY_LIMITS[resource];
  if (observed > limit) {
    throw new ExportCapacityExceededError(resource, limit, observed);
  }
}
