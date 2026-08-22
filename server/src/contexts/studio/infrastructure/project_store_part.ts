import { randomUUID } from "node:crypto";
import { rmSync } from "node:fs";
import { join } from "node:path";
import { desc, eq } from "drizzle-orm";

import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import type {
  AddProjectInput,
  DocumentWithCurrent,
  ProjectScope,
} from "../application/ports/studio_store.js";
import { documents, projects } from "./db/schema.js";
import {
  insertRevision,
  type ProjectRow,
  scopeCondition,
  scopedProject,
} from "./db/studio_query_helpers.js";

/**
 * The project half of the Drizzle studio store (mirrors the Python
 * ProjectRepositoryMixin): creation with the seed document/revision in one
 * transaction, updated_at-descending lists, and deletion that cascades rows
 * and removes the project's export directory after the commit.
 */
export class ProjectStorePart {
  protected readonly db: StudioSqliteDatabase;
  protected readonly dataDirectory: string;

  constructor(db: StudioSqliteDatabase, dataDirectory: string) {
    this.db = db;
    this.dataDirectory = dataDirectory;
  }

  addProject(scope: ProjectScope, input: AddProjectInput) {
    return this.db.transaction((tx) => {
      const project: typeof projects.$inferInsert = {
        id: randomUUID(),
        ownerId: scope.ownerId,
        guestSessionId: scope.guestSessionId,
        title: input.title,
        description: input.description,
        settingsJson: input.settingsJson,
        importHash: null,
        createdAt: input.now,
        updatedAt: input.now,
      };
      tx.insert(projects).values(project).run();
      const seeded: DocumentWithCurrent[] = [];
      if (input.seed !== null) {
        const document: typeof documents.$inferInsert = {
          id: randomUUID(),
          projectId: project.id,
          kind: input.seed.kind,
          title: input.seed.title,
          position: 1,
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
        seeded.push({
          id: document.id,
          projectId: project.id,
          kind: input.seed.kind,
          title: input.seed.title,
          position: 1,
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

  dropProject(scope: ProjectScope, projectId: string): void {
    this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      // Cascades remove documents and revisions; the export tree belongs to
      // the deleted project alone and is removed after the commit.
      tx.delete(projects).where(eq(projects.id, project.id)).run();
    });
    rmSync(join(this.dataDirectory, "exports", projectId), { recursive: true, force: true });
  }
}
