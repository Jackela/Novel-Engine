import { randomUUID } from "node:crypto";
import { and, desc, eq } from "drizzle-orm";

import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import type {
  AddDocumentInput,
  AdvanceDocumentInput,
  DocumentMatchRecord,
  DocumentWithCurrent,
  ProjectScope,
  RevisionPageInput,
  RevisionSummaryPage,
} from "../application/ports/studio_store.js";
import { revisionPageLimit } from "../application/ports/studio_store.js";
import { DuplicateDocumentError, NotFoundError, SnapshotConflict } from "../domain/exceptions.js";
import { DEFAULT_LORE_STATUS } from "../domain/kinds.js";
import { assertStoredRevisionWordCount } from "../domain/revision_word_count.js";
import { advanceDocumentInTransaction } from "./db/document_revision_writes.js";
import {
  clearDocumentIndex,
  matchDocumentIndex,
  refreshDocumentIndex,
} from "./db/document_search.js";
import { documentRevisions, documents, projects, snapshotDocuments } from "./db/schema.js";
import {
  assertOutlineBeatCapacity,
  assertProjectDocumentCapacity,
  assertVolumeChapterCapacity,
} from "./db/structure_capacity_checks.js";
import {
  documentsWithCurrent,
  documentWithCurrent,
  insertRevision,
  isUniqueViolation,
  type RevisionRow,
  scopedCurrentDocument,
  scopedDocument,
  scopedProject,
} from "./db/studio_query_helpers.js";
import { buildRevisionSummariesQuery } from "./revision_page_queries.js";

/**
 * The document, revision, and FTS half of the Drizzle studio store. Every
 * mutation keeps the relational rows and the FTS5 index in one transaction.
 */
export class DocumentStorePart {
  protected readonly db: StudioSqliteDatabase;

  constructor(db: StudioSqliteDatabase) {
    this.db = db;
  }

  findDocuments(scope: ProjectScope, projectId: string): DocumentWithCurrent[] {
    return this.db.transaction((tx) => {
      scopedProject(tx, scope, projectId);
      return documentsWithCurrent(tx, projectId);
    });
  }

  findDocument(scope: ProjectScope, projectId: string, documentId: string): DocumentWithCurrent {
    return this.db.transaction((tx) => {
      scopedProject(tx, scope, projectId);
      return documentWithCurrent(tx, projectId, documentId);
    });
  }

  readCurrentDocument(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
  ): DocumentWithCurrent {
    return this.db.transaction((tx) => scopedCurrentDocument(tx, scope, projectId, documentId));
  }

  addDocument(scope: ProjectScope, projectId: string, input: AddDocumentInput) {
    try {
      return this.db.transaction((tx) => {
        const project = scopedProject(tx, scope, projectId);
        // Capacity refusals precede every insert: no row, revision, index
        // entry, or project timestamp survives an over-budget create (#461).
        assertProjectDocumentCapacity(tx, project.id);
        if (input.kind === "chapter" && input.volumeId !== null) {
          assertVolumeChapterCapacity(tx, input.volumeId);
        }
        assertOutlineBeatCapacity(input.kind, input.contentMarkdown);
        const document: typeof documents.$inferInsert = {
          id: randomUUID(),
          projectId: project.id,
          kind: input.kind,
          title: input.title,
          position: input.position,
          volumeId: input.volumeId,
          currentRevisionId: null,
          createdAt: input.now,
          updatedAt: input.now,
        };
        tx.insert(documents).values(document).run();
        const revision = insertRevision(tx, {
          documentId: document.id,
          parentRevisionId: null,
          revisionNumber: 1,
          contentMarkdown: input.contentMarkdown,
          metadataJson: input.metadataJson,
          source: "author",
          now: input.now,
        });
        tx.update(documents)
          .set({ currentRevisionId: revision.id, updatedAt: input.now })
          .where(eq(documents.id, document.id))
          .run();
        refreshDocumentIndex(tx, {
          documentId: document.id,
          projectId: project.id,
          title: input.title,
          content: input.contentMarkdown,
        });
        tx.update(projects).set({ updatedAt: input.now }).where(eq(projects.id, project.id)).run();
        return {
          id: document.id,
          projectId: project.id,
          kind: input.kind,
          title: input.title,
          position: input.position,
          volumeId: input.volumeId,
          beatRef: null,
          loreAliasesJson: "[]",
          loreStatus: DEFAULT_LORE_STATUS,
          currentRevisionId: revision.id,
          createdAt: input.now,
          updatedAt: input.now,
          currentRevision: revision,
        };
      });
    } catch (error) {
      if (isUniqueViolation(error)) {
        throw new DuplicateDocumentError(input.kind, input.title);
      }
      throw error;
    }
  }

  advanceDocument(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    input: AdvanceDocumentInput,
  ): DocumentWithCurrent {
    return this.db.transaction((tx) =>
      advanceDocumentInTransaction(tx, scope, projectId, documentId, input),
    );
  }

  dropDocument(scope: ProjectScope, projectId: string, documentId: string): void {
    this.db.transaction((tx) => {
      const document = scopedDocument(tx, scope, projectId, documentId);
      const snapshotReference = tx
        .select({ id: snapshotDocuments.id })
        .from(snapshotDocuments)
        .where(eq(snapshotDocuments.documentId, document.id))
        .get();
      if (snapshotReference !== undefined) {
        throw new SnapshotConflict();
      }
      // The FTS table carries no FK; its row leaves in this same transaction.
      clearDocumentIndex(tx, document.id);
      tx.delete(documents).where(eq(documents.id, document.id)).run();
    });
  }

  setBeatReference(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    input: { beatRef: string | null; now: Date },
  ): DocumentWithCurrent {
    return this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      const document = scopedDocument(tx, scope, projectId, documentId);
      if (document.kind !== "chapter") {
        throw new InvalidOperationError("Only chapters associate with outline beats.");
      }
      tx.update(documents)
        .set({ beatRef: input.beatRef, updatedAt: input.now })
        .where(eq(documents.id, document.id))
        .run();
      tx.update(projects).set({ updatedAt: input.now }).where(eq(projects.id, project.id)).run();
      return documentWithCurrent(tx, project.id, document.id);
    });
  }

  matchProjectDocuments(
    scope: ProjectScope,
    projectId: string,
    matchQuery: string,
  ): DocumentMatchRecord[] {
    return this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      return matchDocumentIndex(tx, project.id, matchQuery);
    });
  }

  nextPosition(
    _scope: ProjectScope,
    projectId: string,
    kind: string,
    volumeId?: string | null,
  ): number {
    // Chapters position within their target volume; other kinds stay flat.
    if (kind === "chapter" && volumeId !== undefined && volumeId !== null) {
      const inVolume = this.db
        .select({ position: documents.position })
        .from(documents)
        .where(and(eq(documents.volumeId, volumeId), eq(documents.kind, kind)))
        .orderBy(desc(documents.position))
        .limit(1)
        .all();
      return (inVolume[0]?.position ?? 0) + 1;
    }
    const rows = this.db
      .select({ position: documents.position })
      .from(documents)
      .where(and(eq(documents.projectId, projectId), eq(documents.kind, kind)))
      .orderBy(desc(documents.position))
      .limit(1)
      .all();
    return (rows[0]?.position ?? 0) + 1;
  }

  findRevisionSummaries(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    input: RevisionPageInput,
  ): RevisionSummaryPage {
    const limit = revisionPageLimit(input.limit);
    return this.db.transaction((tx) => {
      scopedDocument(tx, scope, projectId, documentId);
      const rows = buildRevisionSummariesQuery(tx, documentId, { ...input, limit }).all();
      const revisions = rows.slice(0, limit).map((row) => ({
        ...row,
        wordCount: assertStoredRevisionWordCount(row.wordCount),
      }));
      const boundary = revisions.at(-1);
      return {
        revisions,
        nextCursor:
          rows.length > limit && boundary !== undefined
            ? { revisionNumber: boundary.revisionNumber, id: boundary.id }
            : null,
      };
    });
  }

  findRevision(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    revisionId: string,
  ): RevisionRow {
    return this.db.transaction((tx) => {
      scopedDocument(tx, scope, projectId, documentId);
      const row = tx
        .select({ revision: documentRevisions })
        .from(documentRevisions)
        .innerJoin(documents, eq(documentRevisions.documentId, documents.id))
        .where(
          and(
            eq(documentRevisions.id, revisionId),
            eq(documentRevisions.documentId, documentId),
            eq(documents.projectId, projectId),
          ),
        )
        .get();
      if (row === undefined) {
        throw new NotFoundError("Revision not found.");
      }
      return row.revision;
    });
  }
}
