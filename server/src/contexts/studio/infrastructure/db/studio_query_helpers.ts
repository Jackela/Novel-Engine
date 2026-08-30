import { randomUUID } from "node:crypto";
import { and, eq } from "drizzle-orm";

import type { StudioSqliteDatabase } from "../../../../shared/infrastructure/db/connection.js";
import type { DocumentWithCurrent, ProjectScope } from "../../application/ports/studio_store.js";
import { NotFoundError } from "../../domain/exceptions.js";
import { documentRevisions, documents, projects, volumes } from "./schema.js";

export type ProjectRow = typeof projects.$inferSelect;
export type DocumentRow = typeof documents.$inferSelect;
export type RevisionRow = typeof documentRevisions.$inferSelect;
export type VolumeRow = typeof volumes.$inferSelect;

/** The transaction executor handed to store callbacks. */
export type Tx = Parameters<Parameters<StudioSqliteDatabase["transaction"]>[0]>[0];

/** SQLite's unique-constraint violation family, surfaced by better-sqlite3. */
export function isUniqueViolation(error: unknown): boolean {
  return (
    error !== null &&
    typeof error === "object" &&
    (error as { code?: unknown }).code === "SQLITE_CONSTRAINT_UNIQUE"
  );
}

export function scopeCondition(scope: ProjectScope) {
  return eq(projects.ownerId, scope.ownerId);
}

/** Fetch a project scoped to the principal, or raise not-found. */
export function scopedProject(tx: Tx, scope: ProjectScope, projectId: string): ProjectRow {
  const row = tx
    .select()
    .from(projects)
    .where(and(eq(projects.id, projectId), scopeCondition(scope)))
    .get();
  if (row === undefined) {
    throw new NotFoundError("Project not found.");
  }
  return row;
}

/** Fetch a volume through its project so scoping applies to both. */
export function scopedVolume(
  tx: Tx,
  scope: ProjectScope,
  projectId: string,
  volumeId: string,
): VolumeRow {
  const row = tx
    .select({ volume: volumes })
    .from(volumes)
    .innerJoin(projects, eq(volumes.projectId, projects.id))
    .where(and(eq(volumes.id, volumeId), eq(projects.id, projectId), scopeCondition(scope)))
    .get();
  if (row === undefined) {
    throw new NotFoundError("Volume not found.");
  }
  return row.volume;
}

/** Fetch a document through its project so scoping applies to both. */
export function scopedDocument(
  tx: Tx,
  scope: ProjectScope,
  projectId: string,
  documentId: string,
): DocumentRow {
  const row = tx
    .select({ document: documents })
    .from(documents)
    .innerJoin(projects, eq(documents.projectId, projects.id))
    .where(and(eq(documents.id, documentId), eq(projects.id, projectId), scopeCondition(scope)))
    .get();
  if (row === undefined) {
    throw new NotFoundError(
      `No document '${documentId}' exists in project '${projectId}': the id does not exist ` +
        `there, or the document belongs to a different project.`,
    );
  }
  return row.document;
}

/**
 * Composite reading-order key (ADR-0005): chapters read volume by volume and
 * in-volume position first; non-chapter documents keep the flat kind/position
 * ordering outside volumes.
 */
export interface ReadingOrderKey {
  readonly kind: string;
  readonly position: number;
  readonly createdAt: Date;
  readonly id: string;
  /** Position of the owning volume; null for documents outside volumes. */
  readonly volumePosition: number | null;
}

export function compareReadingOrder(left: ReadingOrderKey, right: ReadingOrderKey): number {
  // Only chapters belong to volumes; they always read ahead of the flat,
  // non-chapter kinds (matching the previous alphabetical chapter-first list).
  if (left.kind !== right.kind && (left.kind === "chapter" || right.kind === "chapter")) {
    return left.kind === "chapter" ? -1 : 1;
  }
  if (left.kind === "chapter") {
    const leftVolume = left.volumePosition ?? Number.POSITIVE_INFINITY;
    const rightVolume = right.volumePosition ?? Number.POSITIVE_INFINITY;
    if (leftVolume !== rightVolume) return leftVolume - rightVolume;
  } else if (left.kind !== right.kind) {
    return left.kind.localeCompare(right.kind);
  }
  return (
    left.position - right.position ||
    left.createdAt.getTime() - right.createdAt.getTime() ||
    left.id.localeCompare(right.id)
  );
}

/** Documents with their current revision in the composite reading order. */
export function documentsWithCurrent(tx: Tx, projectId: string): DocumentWithCurrent[] {
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
      ...row.document,
      currentRevision: row.revision,
      volumePosition: row.volumePosition ?? null,
    }))
    .sort(compareReadingOrder)
    .map(({ volumePosition: _volumePosition, ...record }) => record);
}

/** Append one immutable revision row (the sole revision write path). */
export function insertRevision(
  tx: Tx,
  input: {
    documentId: string;
    parentRevisionId: string | null;
    revisionNumber: number;
    contentMarkdown: string;
    metadataJson: string;
    source: string;
    now: Date;
  },
): RevisionRow {
  const revision: typeof documentRevisions.$inferInsert = {
    id: randomUUID(),
    documentId: input.documentId,
    parentRevisionId: input.parentRevisionId,
    revisionNumber: input.revisionNumber,
    contentMarkdown: input.contentMarkdown,
    metadataJson: input.metadataJson,
    source: input.source,
    createdAt: input.now,
  };
  tx.insert(documentRevisions).values(revision).run();
  return revision as RevisionRow;
}
