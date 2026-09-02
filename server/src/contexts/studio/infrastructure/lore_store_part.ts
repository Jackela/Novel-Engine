import { eq } from "drizzle-orm";

import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import { isLoreEntryKind } from "../application/lorebook.js";
import type { SetLoreAliasesInput, SetLoreStatusInput } from "../application/ports/lore_store.js";
import type { DocumentWithCurrent, ProjectScope } from "../application/ports/studio_store.js";
import { documents, projects } from "./db/schema.js";
import { documentWithCurrent, scopedDocument, scopedProject } from "./db/studio_query_helpers.js";

/**
 * The lorebook half of the Drizzle studio store (#315): document-level alias
 * and lifecycle-status state for character/world entries. Writes mint no
 * revision and touch no immutable history — aliases are prompt keys and the
 * status is injection gating, not authoring content (#444).
 */
export class LoreStorePart {
  protected readonly db: StudioSqliteDatabase;

  constructor(db: StudioSqliteDatabase) {
    this.db = db;
  }

  setLoreAliases(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    input: SetLoreAliasesInput,
  ): DocumentWithCurrent {
    return this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      const document = scopedDocument(tx, scope, projectId, documentId);
      if (!isLoreEntryKind(document.kind)) {
        throw new InvalidOperationError(
          "Only character and world documents carry lorebook aliases.",
        );
      }
      tx.update(documents)
        .set({ loreAliasesJson: JSON.stringify(input.aliases), updatedAt: input.now })
        .where(eq(documents.id, document.id))
        .run();
      tx.update(projects).set({ updatedAt: input.now }).where(eq(projects.id, project.id)).run();
      return documentWithCurrent(tx, project.id, document.id);
    });
  }

  setLoreStatus(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    input: SetLoreStatusInput,
  ): DocumentWithCurrent {
    return this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      const document = scopedDocument(tx, scope, projectId, documentId);
      if (!isLoreEntryKind(document.kind)) {
        throw new InvalidOperationError(
          "Only character and world documents carry a lore lifecycle status.",
        );
      }
      tx.update(documents)
        .set({ loreStatus: input.status, updatedAt: input.now })
        .where(eq(documents.id, document.id))
        .run();
      tx.update(projects).set({ updatedAt: input.now }).where(eq(projects.id, project.id)).run();
      return documentWithCurrent(tx, project.id, document.id);
    });
  }
}
