import { randomUUID } from "node:crypto";
import { and, asc, desc, eq } from "drizzle-orm";

import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import type {
  AddDocumentInput,
  AddJobInput,
  AddUsageEventInput,
  AdvanceDocumentInput,
  DocumentMatchRecord,
  DocumentWithCurrent,
  JobRecord,
  ProjectScope,
  StudioStore,
} from "../application/ports/studio_store.js";
import {
  DuplicateDocumentError,
  NotFoundError,
  RevisionConflictError,
} from "../domain/exceptions.js";
import {
  clearDocumentIndex,
  matchDocumentIndex,
  refreshDocumentIndex,
} from "./db/document_search.js";
import { documentRevisions, documents, projects } from "./db/schema.js";
import {
  documentsWithCurrent,
  insertRevision,
  isUniqueViolation,
  type RevisionRow,
  scopedDocument,
  scopedProject,
  type Tx,
} from "./db/studio_query_helpers.js";
import { JobStorePart } from "./job_store_part.js";
import { ProjectStorePart } from "./project_store_part.js";

export interface DrizzleStudioStoreOptions {
  database: StudioSqliteDatabase;
  /** Data directory owning `novel-engine.sqlite3`; export trees live beneath it. */
  dataDirectory: string;
}

/**
 * Drizzle implementation of the authoring StudioStore (document and revision
 * half; projects live in ProjectStorePart, workflow jobs in JobStorePart):
 * every mutation runs in one transaction — revision create plus document
 * advance are atomic — and unique violations surface as domain conflicts.
 */
export class DrizzleStudioStore extends ProjectStorePart implements StudioStore {
  private readonly workflowJobs: JobStorePart;

  constructor(options: DrizzleStudioStoreOptions) {
    super(options.database, options.dataDirectory);
    this.workflowJobs = new JobStorePart(options.database);
  }

  addJob(scope: ProjectScope, input: AddJobInput): JobRecord {
    return this.workflowJobs.addJob(scope, input);
  }

  addUsageEvent(scope: ProjectScope, input: AddUsageEventInput): void {
    this.workflowJobs.addUsageEvent(scope, input);
  }

  findJob(scope: ProjectScope, projectId: string, jobId: string): JobRecord {
    return this.workflowJobs.findJob(scope, projectId, jobId);
  }

  setJobResult(
    scope: ProjectScope,
    projectId: string,
    jobId: string,
    resultJson: string,
    now: Date,
  ): JobRecord {
    return this.workflowJobs.setJobResult(scope, projectId, jobId, resultJson, now);
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

  addDocument(scope: ProjectScope, projectId: string, input: AddDocumentInput) {
    try {
      return this.db.transaction((tx) => {
        const project = scopedProject(tx, scope, projectId);
        const document: typeof documents.$inferInsert = {
          id: randomUUID(),
          projectId: project.id,
          kind: input.kind,
          title: input.title,
          position: input.position,
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
    return this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      const document = scopedDocument(tx, scope, projectId, documentId);
      if (document.currentRevisionId !== input.baseRevisionId) {
        throw new RevisionConflictError(document.currentRevisionId);
      }
      const current = tx
        .select()
        .from(documentRevisions)
        .where(eq(documentRevisions.id, document.currentRevisionId ?? ""))
        .get();
      if (current === undefined) {
        throw new NotFoundError("Current revision not found.");
      }
      const revision = insertRevision(tx, {
        documentId: document.id,
        parentRevisionId: document.currentRevisionId,
        revisionNumber: current.revisionNumber + 1,
        contentMarkdown: input.contentMarkdown,
        metadataJson: input.metadataJson,
        source: input.source,
        now: input.now,
      });
      const title = input.title ?? document.title;
      tx.update(documents)
        .set({ currentRevisionId: revision.id, title, updatedAt: input.now })
        .where(eq(documents.id, document.id))
        .run();
      refreshDocumentIndex(tx, {
        documentId: document.id,
        projectId: project.id,
        title,
        content: input.contentMarkdown,
      });
      tx.update(projects).set({ updatedAt: input.now }).where(eq(projects.id, project.id)).run();
      return {
        ...document,
        title,
        currentRevisionId: revision.id,
        updatedAt: input.now,
        currentRevision: revision,
      };
    });
  }

  dropDocument(scope: ProjectScope, projectId: string, documentId: string): void {
    this.db.transaction((tx) => {
      scopedDocument(tx, scope, projectId, documentId);
      // The FTS table carries no FK; its row leaves in this same transaction.
      clearDocumentIndex(tx, documentId);
      tx.delete(documents).where(eq(documents.id, documentId)).run();
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

  renumberDocuments(
    scope: ProjectScope,
    projectId: string,
    documentIds: string[],
    now: Date,
  ): DocumentWithCurrent[] {
    return this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      const existing = tx.select().from(documents).where(eq(documents.projectId, project.id)).all();
      const byId = new Map(existing.map((row) => [row.id, row]));
      const unique = new Set(documentIds);
      if (
        documentIds.length !== existing.length ||
        unique.size !== documentIds.length ||
        documentIds.some((id) => !byId.has(id))
      ) {
        throw new InvalidOperationError("Reorder must include every project document once.");
      }
      for (const [index, id] of documentIds.entries()) {
        tx.update(documents)
          .set({ position: index + 1, updatedAt: now })
          .where(eq(documents.id, id))
          .run();
      }
      tx.update(projects).set({ updatedAt: now }).where(eq(projects.id, project.id)).run();
      return documentsWithCurrent(tx, project.id).sort(
        (left, right) => documentIds.indexOf(left.id) - documentIds.indexOf(right.id),
      );
    });
  }

  nextPosition(_scope: ProjectScope, projectId: string, kind: string): number {
    const rows = this.db
      .select({ position: documents.position })
      .from(documents)
      .where(and(eq(documents.projectId, projectId), eq(documents.kind, kind)))
      .orderBy(desc(documents.position))
      .limit(1)
      .all();
    return (rows[0]?.position ?? 0) + 1;
  }

  findRevisions(scope: ProjectScope, projectId: string, documentId: string): RevisionRow[] {
    return this.db.transaction((tx) => {
      scopedDocument(tx, scope, projectId, documentId);
      return tx
        .select({ revision: documentRevisions })
        .from(documentRevisions)
        .innerJoin(documents, eq(documentRevisions.documentId, documents.id))
        .where(
          and(eq(documentRevisions.documentId, documentId), eq(documents.projectId, projectId)),
        )
        .orderBy(asc(documentRevisions.revisionNumber))
        .all()
        .map((row) => row.revision);
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

function documentWithCurrent(tx: Tx, projectId: string, documentId: string): DocumentWithCurrent {
  const row = tx
    .select({ document: documents, revision: documentRevisions })
    .from(documents)
    .leftJoin(documentRevisions, eq(documents.currentRevisionId, documentRevisions.id))
    .where(and(eq(documents.id, documentId), eq(documents.projectId, projectId)))
    .get();
  if (row === undefined) {
    throw new NotFoundError("Document not found.");
  }
  return { ...row.document, currentRevision: row.revision };
}
