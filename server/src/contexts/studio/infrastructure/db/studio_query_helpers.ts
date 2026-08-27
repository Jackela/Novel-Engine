import { randomUUID } from "node:crypto";
import { and, asc, eq } from "drizzle-orm";

import type { StudioSqliteDatabase } from "../../../../shared/infrastructure/db/connection.js";
import type { DocumentWithCurrent, ProjectScope } from "../../application/ports/studio_store.js";
import { NotFoundError } from "../../domain/exceptions.js";
import { documentRevisions, documents, projects } from "./schema.js";

export type ProjectRow = typeof projects.$inferSelect;
export type DocumentRow = typeof documents.$inferSelect;
export type RevisionRow = typeof documentRevisions.$inferSelect;

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
    throw new NotFoundError("Document not found.");
  }
  return row.document;
}

/** Documents with their current revision, in the stable (kind, position, created) order. */
export function documentsWithCurrent(tx: Tx, projectId: string): DocumentWithCurrent[] {
  const rows = tx
    .select({ document: documents, revision: documentRevisions })
    .from(documents)
    .leftJoin(documentRevisions, eq(documents.currentRevisionId, documentRevisions.id))
    .where(eq(documents.projectId, projectId))
    .orderBy(asc(documents.kind), asc(documents.position), asc(documents.createdAt))
    .all();
  return rows.map((row) => ({ ...row.document, currentRevision: row.revision }));
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
