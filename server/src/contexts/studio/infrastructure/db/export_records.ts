import { randomUUID } from "node:crypto";
import { and, asc, desc, eq, inArray } from "drizzle-orm";

import { InvalidOperationError } from "../../../../shared/domain/exceptions.js";
import {
  assertCanonicalExportArtifactEvidence,
  isExportArtifactFormat,
} from "../../application/export_artifact_identity.js";
import { sameExportSourceProjection } from "../../application/export_source_identity.js";
import type {
  ExportArtifactFormat,
  ExportArtifactRecord,
  ExportSource,
  ExportSourceDocument,
  PreparedExportArtifact,
} from "../../application/ports/export_store.js";
import { ExportSourceInvalidatedError } from "../../domain/exceptions.js";
import {
  documentRevisions,
  documents,
  exports as exportArtifacts,
  projectSnapshots,
  snapshotDocuments,
  volumes,
} from "./schema.js";
import { compareReadingOrder, type Tx } from "./studio_query_helpers.js";

/** Read the live projection without creating durable snapshot rows. */
export function readCurrentExportDocuments(tx: Tx, projectId: string): ExportSourceDocument[] {
  const rows = tx
    .select({
      document: documents,
      revision: documentRevisions,
      volumePosition: volumes.position,
    })
    .from(documents)
    .leftJoin(documentRevisions, eq(documents.currentRevisionId, documentRevisions.id))
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
    .map(({ row: { document, revision } }, index) => {
      if (
        document.currentRevisionId === null ||
        revision === null ||
        revision.id !== document.currentRevisionId ||
        revision.documentId !== document.id
      ) {
        throw new Error("Every export source document requires a current revision.");
      }
      return {
        documentId: document.id,
        revisionId: revision.id,
        kind: document.kind,
        title: document.title,
        contentMarkdown: revision.contentMarkdown,
        metadataJson: revision.metadataJson,
        position: index + 1,
      };
    });
}

export function findLatestExportSnapshot(tx: Tx, projectId: string) {
  return tx
    .select()
    .from(projectSnapshots)
    .where(and(eq(projectSnapshots.projectId, projectId), eq(projectSnapshots.reason, "export")))
    .orderBy(desc(projectSnapshots.createdAt), desc(projectSnapshots.id))
    .get();
}

export function readExportSnapshotDocuments(tx: Tx, snapshotId: string): ExportSourceDocument[] {
  return tx
    .select({ snapshotDocument: snapshotDocuments, revision: documentRevisions })
    .from(snapshotDocuments)
    .leftJoin(documentRevisions, eq(snapshotDocuments.revisionId, documentRevisions.id))
    .where(eq(snapshotDocuments.snapshotId, snapshotId))
    .orderBy(asc(snapshotDocuments.position), asc(snapshotDocuments.documentId))
    .all()
    .map(({ snapshotDocument, revision }) => {
      if (revision === null || revision.documentId !== snapshotDocument.documentId) {
        throw new Error("Export snapshot references an invalid document revision.");
      }
      return {
        documentId: snapshotDocument.documentId,
        revisionId: snapshotDocument.revisionId,
        kind: snapshotDocument.documentKind,
        title: snapshotDocument.documentTitle,
        contentMarkdown: revision.contentMarkdown,
        metadataJson: snapshotDocument.revisionMetadataJson,
        position: snapshotDocument.position,
      };
    });
}

/** Resolve or create the exact snapshot represented by a captured source. */
export function resolveExportSnapshot(tx: Tx, projectId: string, source: ExportSource): string {
  assertCapturedExportSource(tx, projectId, source.documents);
  if (!source.documents.some((document) => document.kind === "chapter")) {
    throw new InvalidOperationError("A project needs at least one chapter before export.");
  }
  if (source.reuseSnapshotId !== null) {
    const candidate = findExportSnapshot(tx, projectId, source.reuseSnapshotId);
    if (candidate === undefined) throw new Error("Reusable export snapshot disappeared.");
    if (
      !sameExportSourceProjection(readExportSnapshotDocuments(tx, candidate.id), source.documents)
    ) {
      throw new Error("Reusable export snapshot projection changed after capture.");
    }
    return candidate.id;
  }
  const latest = findLatestExportSnapshot(tx, projectId);
  if (
    latest !== undefined &&
    sameExportSourceProjection(readExportSnapshotDocuments(tx, latest.id), source.documents)
  ) {
    return latest.id;
  }
  return writeExportSnapshot(tx, projectId, source.documents, source.capturedAt);
}

export function insertExportArtifact(
  tx: Tx,
  projectId: string,
  snapshotId: string,
  input: PreparedExportArtifact,
  beforeInsert: (artifactId: string) => void = () => {},
): ExportArtifactRecord {
  assertCanonicalExportArtifactEvidence({
    projectId,
    id: input.id,
    format: input.format,
    relativePath: input.relativePath,
    sizeBytes: input.sizeBytes,
    checksumSha256: input.checksumSha256,
  });
  beforeInsert(input.id);
  tx.insert(exportArtifacts)
    .values({
      id: input.id,
      projectId,
      snapshotId,
      format: input.format,
      relativePath: input.relativePath,
      sizeBytes: input.sizeBytes,
      checksumSha256: input.checksumSha256,
      createdAt: input.createdAt,
    })
    .run();
  return toArtifactRecord({ ...input, projectId, snapshotId });
}

export function loadProjectArtifacts(tx: Tx, projectId: string): ExportArtifactRecord[] {
  return tx
    .select()
    .from(exportArtifacts)
    .where(eq(exportArtifacts.projectId, projectId))
    .orderBy(desc(exportArtifacts.createdAt), desc(exportArtifacts.id))
    .all()
    .map(toArtifactRecord);
}

export function loadProjectArtifact(
  tx: Tx,
  projectId: string,
  artifactId: string,
): ExportArtifactRecord | undefined {
  const row = tx
    .select()
    .from(exportArtifacts)
    .where(and(eq(exportArtifacts.id, artifactId), eq(exportArtifacts.projectId, projectId)))
    .get();
  return row === undefined ? undefined : toArtifactRecord(row);
}

function assertCapturedExportSource(
  tx: Tx,
  projectId: string,
  source: readonly ExportSourceDocument[],
): void {
  if (source.length === 0) return;
  const revisions = source.map((item) => item.revisionId);
  const rows = tx
    .select({
      documentId: documents.id,
      revisionId: documentRevisions.id,
      contentMarkdown: documentRevisions.contentMarkdown,
      metadataJson: documentRevisions.metadataJson,
    })
    .from(documents)
    .innerJoin(documentRevisions, eq(documentRevisions.documentId, documents.id))
    .where(and(eq(documents.projectId, projectId), inArray(documentRevisions.id, revisions)))
    .all();
  const available = new Map(rows.map((row) => [`${row.documentId}\u0000${row.revisionId}`, row]));
  for (const document of source) {
    const row = available.get(`${document.documentId}\u0000${document.revisionId}`);
    if (row === undefined) throw new ExportSourceInvalidatedError();
    if (
      row.contentMarkdown !== document.contentMarkdown ||
      row.metadataJson !== document.metadataJson
    ) {
      throw new Error("Persisted immutable export source changed after capture.");
    }
  }
}

function findExportSnapshot(tx: Tx, projectId: string, snapshotId: string) {
  return tx
    .select()
    .from(projectSnapshots)
    .where(
      and(
        eq(projectSnapshots.id, snapshotId),
        eq(projectSnapshots.projectId, projectId),
        eq(projectSnapshots.reason, "export"),
      ),
    )
    .get();
}

function writeExportSnapshot(
  tx: Tx,
  projectId: string,
  documentsToCapture: readonly ExportSourceDocument[],
  createdAt: Date,
): string {
  const snapshotId = randomUUID();
  tx.insert(projectSnapshots)
    .values({ id: snapshotId, projectId, reason: "export", createdAt })
    .run();
  for (const document of documentsToCapture) {
    tx.insert(snapshotDocuments)
      .values({
        id: randomUUID(),
        snapshotId,
        documentId: document.documentId,
        revisionId: document.revisionId,
        documentKind: document.kind,
        documentTitle: document.title,
        revisionMetadataJson: document.metadataJson,
        position: document.position,
      })
      .run();
  }
  return snapshotId;
}

function toArtifactRecord(
  artifact:
    | typeof exportArtifacts.$inferSelect
    | (PreparedExportArtifact & { projectId: string; snapshotId: string }),
): ExportArtifactRecord {
  return {
    id: artifact.id,
    projectId: artifact.projectId,
    snapshotId: artifact.snapshotId,
    format: readArtifactFormat(artifact.format),
    relativePath: artifact.relativePath,
    sizeBytes: artifact.sizeBytes,
    checksumSha256: artifact.checksumSha256,
    createdAt: artifact.createdAt,
  };
}

function readArtifactFormat(format: string): ExportArtifactFormat {
  if (isExportArtifactFormat(format)) return format;
  throw new Error("Export artifact format is invalid.");
}
