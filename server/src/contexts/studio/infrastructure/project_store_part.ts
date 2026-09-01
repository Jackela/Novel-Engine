import { randomUUID } from "node:crypto";
import { and, desc, eq } from "drizzle-orm";

import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import { jobs, usageEvents } from "../../../shared/infrastructure/db/schema.js";
import type {
  AddImportedProjectInput,
  AddProjectInput,
  DocumentWithCurrent,
  ProjectScope,
} from "../application/ports/studio_store.js";
import { DEFAULT_LORE_STATUS } from "../domain/kinds.js";
import { clearProjectDocumentIndex, refreshDocumentIndex } from "./db/document_search.js";
import { documents, projects } from "./db/schema.js";
import {
  documentsWithCurrent,
  insertRevision,
  type ProjectRow,
  scopeCondition,
  scopedProject,
} from "./db/studio_query_helpers.js";
import { DEFAULT_VOLUME_TITLE, insertVolume } from "./volume_store_part.js";

/**
 * The project half of the Drizzle studio store (mirrors the Python
 * ProjectRepositoryMixin): creation with the seed document/revision in one
 * transaction, updated_at-descending lists, and deletion that cascades rows
 * in the same database transaction. Filesystem cleanup belongs to the
 * application service because it cannot join SQLite's transaction.
 */
export class ProjectStorePart {
  protected readonly db: StudioSqliteDatabase;

  constructor(db: StudioSqliteDatabase) {
    this.db = db;
  }

  addProject(scope: ProjectScope, input: AddProjectInput) {
    return this.db.transaction((tx) => {
      const project: typeof projects.$inferInsert = {
        id: randomUUID(),
        ownerId: scope.ownerId,
        title: input.title,
        description: input.description,
        settingsJson: input.settingsJson,
        importHash: null,
        createdAt: input.now,
        updatedAt: input.now,
      };
      tx.insert(projects).values(project).run();
      // ADR-0005: the default volume exists before any seed chapter, so no
      // document is ever unplaced.
      const defaultVolume = insertVolume(tx, {
        projectId: project.id,
        title: DEFAULT_VOLUME_TITLE,
        position: 1,
        now: input.now,
      });
      const seeded: DocumentWithCurrent[] = [];
      if (input.seed !== null) {
        const document: typeof documents.$inferInsert = {
          id: randomUUID(),
          projectId: project.id,
          kind: input.seed.kind,
          title: input.seed.title,
          position: 1,
          volumeId: defaultVolume.id,
          currentRevisionId: null,
          createdAt: input.now,
          updatedAt: input.now,
        };
        tx.insert(documents).values(document).run();
        const revision = insertRevision(tx, {
          documentId: document.id,
          parentRevisionId: null,
          revisionNumber: 1,
          contentMarkdown: input.seed.contentMarkdown,
          metadataJson: input.seed.metadataJson,
          source: "author",
          now: input.now,
        });
        tx.update(documents)
          .set({ currentRevisionId: revision.id })
          .where(eq(documents.id, document.id))
          .run();
        refreshDocumentIndex(tx, {
          documentId: document.id,
          projectId: project.id,
          title: input.seed.title,
          content: input.seed.contentMarkdown,
        });
        seeded.push({
          id: document.id,
          projectId: project.id,
          kind: input.seed.kind,
          title: input.seed.title,
          position: 1,
          volumeId: defaultVolume.id,
          beatRef: null,
          loreAliasesJson: "[]",
          loreStatus: DEFAULT_LORE_STATUS,
          currentRevisionId: revision.id,
          createdAt: input.now,
          updatedAt: input.now,
          currentRevision: revision,
        });
      }
      return { project: project as ProjectRow, documents: seeded };
    });
  }

  findProjects(scope: ProjectScope): ProjectRow[] {
    return this.db
      .select()
      .from(projects)
      .where(scopeCondition(scope))
      .orderBy(desc(projects.updatedAt))
      .all();
  }

  findProject(scope: ProjectScope, projectId: string): ProjectRow {
    return this.db.transaction((tx) => scopedProject(tx, scope, projectId));
  }

  /** The principal-scoped idempotency probe: at most one row per (scope, hash). */
  findProjectByImportHash(scope: ProjectScope, importHash: string): ProjectRow | null {
    return (
      this.db
        .select()
        .from(projects)
        .where(and(eq(projects.importHash, importHash), scopeCondition(scope)))
        .get() ?? null
    );
  }

  /**
   * The single legacy-import write: the project row carries its import hash
   * from the start, and every chapter document, revision, and FTS entry
   * commits in the same transaction — or not at all.
   */
  addImportedProject(
    scope: ProjectScope,
    input: AddImportedProjectInput,
  ): { project: ProjectRow; documents: DocumentWithCurrent[] } {
    return this.db.transaction((tx) => {
      const project: typeof projects.$inferInsert = {
        id: randomUUID(),
        ownerId: scope.ownerId,
        title: input.title,
        description: input.description,
        settingsJson: input.settingsJson,
        importHash: input.importHash,
        createdAt: input.now,
        updatedAt: input.now,
      };
      tx.insert(projects).values(project).run();
      // Legacy chapters land in one default volume (ADR-0005 import seeding).
      const defaultVolume = insertVolume(tx, {
        projectId: project.id,
        title: DEFAULT_VOLUME_TITLE,
        position: 1,
        now: input.now,
      });
      for (const [index, chapter] of input.chapters.entries()) {
        const position = index + 1;
        const title = `Chapter ${position}`;
        const document: typeof documents.$inferInsert = {
          id: randomUUID(),
          projectId: project.id,
          kind: "chapter",
          title,
          position,
          volumeId: defaultVolume.id,
          currentRevisionId: null,
          createdAt: input.now,
          updatedAt: input.now,
        };
        tx.insert(documents).values(document).run();
        const revision = insertRevision(tx, {
          documentId: document.id,
          parentRevisionId: null,
          revisionNumber: 1,
          contentMarkdown: chapter.contentMarkdown,
          metadataJson: chapter.metadataJson,
          source: "author",
          now: input.now,
        });
        tx.update(documents)
          .set({ currentRevisionId: revision.id })
          .where(eq(documents.id, document.id))
          .run();
        refreshDocumentIndex(tx, {
          documentId: document.id,
          projectId: project.id,
          title,
          content: chapter.contentMarkdown,
        });
      }
      return {
        project: project as ProjectRow,
        documents: documentsWithCurrent(tx, project.id),
      };
    });
  }

  dropProject(scope: ProjectScope, projectId: string): void {
    this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      // The FTS table and the workflow jobs reference the project without a
      // cross-schema FK, so their rows leave explicitly in this same
      // transaction; cascades remove documents and revisions. Export-file
      // cleanup runs only after this database commit succeeds.
      clearProjectDocumentIndex(tx, project.id);
      tx.delete(usageEvents).where(eq(usageEvents.project_id, project.id)).run();
      tx.delete(jobs).where(eq(jobs.project_id, project.id)).run();
      tx.delete(projects).where(eq(projects.id, project.id)).run();
    });
  }
}
