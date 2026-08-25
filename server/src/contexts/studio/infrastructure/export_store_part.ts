import { randomUUID } from "node:crypto";
import { and, asc, desc, eq } from "drizzle-orm";

import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import type {
  AppendArtifactInput,
  ExportArtifactFormat,
  ExportArtifactRecord,
  ExportSnapshotDocument,
  ExportSnapshotMaterialization,
  ExportStore,
} from "../application/ports/export_store.js";
import type { ProjectScope } from "../application/ports/studio_store.js";
import { NotFoundError } from "../domain/exceptions.js";
import {
  documentRevisions,
  documents,
  exports as exportArtifacts,
  projectSnapshots,
  snapshotDocuments,
} from "./db/schema.js";
import { scopedProject, type Tx } from "./db/studio_query_helpers.js";

interface CurrentDocument {
  documentId: string;
  revisionId: string;
  kind: string;
  title: string;
  metadataJson: string;
  position: number;
}

/**
 * Immutable export snapshot and artifact persistence, kept separate from the
 * authoring StudioStore so rendering can evolve without broadening that port.
 */
export class ExportStorePart implements ExportStore {
  private readonly db: StudioSqliteDatabase;

  constructor(db: StudioSqliteDatabase) {
    this.db = db;
  }

  materializeArtifactSnapshot(
    scope: ProjectScope,
    projectId: string,
    now: Date,
  ): ExportSnapshotMaterialization {
    return this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      const current = readCurrentDocuments(tx, project.id);
      const latest = findLatestExportSnapshot(tx, project.id);
      if (latest !== undefined) {
        const captured = readSnapshotDocuments(tx, latest.id);
        if (hasMatchingRevisionMap(current, captured)) {
          return { snapshotId: latest.id, documents: captured };
        }
      }
      const snapshotId = writeExportSnapshot(tx, project.id, current, now);
      return { snapshotId, documents: readSnapshotDocuments(tx, snapshotId) };
    });
  }

  appendArtifact(
    scope: ProjectScope,
    projectId: string,
    input: AppendArtifactInput,
  ): ExportArtifactRecord {
    return this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      const snapshot = tx
        .select({ id: projectSnapshots.id })
        .from(projectSnapshots)
        .where(
          and(
            eq(projectSnapshots.id, input.snapshotId),
            eq(projectSnapshots.projectId, project.id),
            eq(projectSnapshots.reason, "export"),
          ),
        )
        .get();
      if (snapshot === undefined) {
        throw new NotFoundError("Export snapshot not found.");
      }
      tx.insert(exportArtifacts)
        .values({
          id: input.id,
          projectId: project.id,
          snapshotId: snapshot.id,
          format: input.format,
          relativePath: input.relativePath,
          sizeBytes: input.sizeBytes,
          checksumSha256: input.checksumSha256,
          createdAt: input.createdAt,
        })
        .run();
      return toArtifactRecord({ ...input, projectId: project.id });
    });
  }

  listProjectArtifacts(scope: ProjectScope, projectId: string): ExportArtifactRecord[] {
    return this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      return tx
        .select()
        .from(exportArtifacts)
        .where(eq(exportArtifacts.projectId, project.id))
        .orderBy(desc(exportArtifacts.createdAt), desc(exportArtifacts.id))
        .all()
        .map(toArtifactRecord);
    });
  }

  findProjectArtifact(
    scope: ProjectScope,
    projectId: string,
    artifactId: string,
  ): ExportArtifactRecord {
    return this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      const artifact = tx
        .select()
        .from(exportArtifacts)
        .where(and(eq(exportArtifacts.id, artifactId), eq(exportArtifacts.projectId, project.id)))
        .get();
      if (artifact === undefined) {
        throw new NotFoundError("Export artifact not found.");
      }
      return toArtifactRecord(artifact);
    });
  }
}

function readCurrentDocuments(tx: Tx, projectId: string): CurrentDocument[] {
  const rows = tx
    .select({ document: documents, revision: documentRevisions })
    .from(documents)
    .leftJoin(documentRevisions, eq(documents.currentRevisionId, documentRevisions.id))
    .where(eq(documents.projectId, projectId))
    .orderBy(asc(documents.position), asc(documents.createdAt), asc(documents.id))
    .all();
  return rows.map(({ document, revision }) => {
    if (
      document.currentRevisionId === null ||
      revision === null ||
      revision.id !== document.currentRevisionId ||
      revision.documentId !== document.id
    ) {
      throw new InvalidOperationError(
        "Every export snapshot document requires a current revision.",
      );
    }
    return {
      documentId: document.id,
      revisionId: revision.id,
      kind: document.kind,
      title: document.title,
      metadataJson: revision.metadataJson,
      position: document.position,
    };
  });
}

function findLatestExportSnapshot(tx: Tx, projectId: string) {
  return tx
    .select()
    .from(projectSnapshots)
    .where(and(eq(projectSnapshots.projectId, projectId), eq(projectSnapshots.reason, "export")))
    .orderBy(desc(projectSnapshots.createdAt), desc(projectSnapshots.id))
    .get();
}

function readSnapshotDocuments(tx: Tx, snapshotId: string): ExportSnapshotDocument[] {
  const rows = tx
    .select({ snapshotDocument: snapshotDocuments, revision: documentRevisions })
    .from(snapshotDocuments)
    .leftJoin(documentRevisions, eq(snapshotDocuments.revisionId, documentRevisions.id))
    .where(eq(snapshotDocuments.snapshotId, snapshotId))
    .orderBy(asc(snapshotDocuments.position), asc(snapshotDocuments.documentId))
    .all();
  return rows.map(({ snapshotDocument, revision }) => {
    if (revision === null || revision.documentId !== snapshotDocument.documentId) {
      throw new InvalidOperationError("Export snapshot references an invalid document revision.");
    }
    return {
      snapshotDocumentId: snapshotDocument.id,
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

function hasMatchingRevisionMap(
  current: readonly CurrentDocument[],
  captured: readonly ExportSnapshotDocument[],
): boolean {
  if (current.length !== captured.length) {
    return false;
  }
  const capturedByDocumentId = new Map(
    captured.map((document) => [document.documentId, document.revisionId]),
  );
  return (
    capturedByDocumentId.size === current.length &&
    current.every(
      (document) => capturedByDocumentId.get(document.documentId) === document.revisionId,
    )
  );
}

function writeExportSnapshot(
  tx: Tx,
  projectId: string,
  current: readonly CurrentDocument[],
  now: Date,
): string {
  const snapshotId = randomUUID();
  tx.insert(projectSnapshots)
    .values({ id: snapshotId, projectId, reason: "export", createdAt: now })
    .run();
  for (const document of current) {
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
  artifact: typeof exportArtifacts.$inferSelect | (AppendArtifactInput & { projectId: string }),
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
  if (format === "markdown" || format === "docx" || format === "epub") {
    return format;
  }
  throw new InvalidOperationError("Export artifact format is invalid.");
}
