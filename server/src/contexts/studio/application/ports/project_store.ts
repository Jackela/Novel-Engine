import type { DocumentWithCurrent } from "./document_store.js";
import type { ProjectCatalogStore } from "./project_catalog_store.js";
import type { ProjectShellRecord } from "./project_shell_records.js";
import type { ProjectUpdateStore } from "./project_update_store.js";
import type { ProjectScope } from "./studio_store.js";

/** Persistence-neutral row shape handed to the application layer. */
export interface ProjectRecord {
  id: string;
  ownerId: string;
  title: string;
  description: string;
  settingsJson: string;
  importHash: string | null;
  createdAt: Date;
  updatedAt: Date;
}

export interface AddProjectInput {
  title: string;
  description: string;
  settingsJson: string;
  /** Seed document/revision written in the same transaction as the project. */
  seed: { kind: string; title: string; contentMarkdown: string; metadataJson: string } | null;
  now: Date;
}

/** One imported chapter: content plus its persisted metadata JSON. */
interface ImportedChapterInput {
  contentMarkdown: string;
  metadataJson: string;
}

/**
 * The whole legacy-import write: the project row already carries its import
 * hash, and every chapter document/revision lands in the same transaction.
 */
export interface AddImportedProjectInput {
  title: string;
  description: string;
  settingsJson: string;
  importHash: string;
  chapters: ImportedChapterInput[];
  now: Date;
}

/**
 * Project-port of the authoring core: creation with the seed document and
 * default volume, the bounded owner catalog, scalar updates, the structural
 * shell read, and deletion that cascades rows in one transaction. Catalog
 * pagination (#458) and scalar updates extend the same part, so their focused
 * ports compose here.
 */
export interface ProjectStore extends ProjectUpdateStore, ProjectCatalogStore {
  addProject(
    scope: ProjectScope,
    input: AddProjectInput,
  ): {
    project: ProjectRecord;
    documents: DocumentWithCurrent[];
  };
  findProject(scope: ProjectScope, projectId: string): ProjectRecord;
  readProjectShell(scope: ProjectScope, projectId: string): ProjectShellRecord;
  /** Existing project of this principal carrying the given import hash, if any. */
  findProjectByImportHash(scope: ProjectScope, importHash: string): ProjectRecord | null;
  /**
   * Transactional legacy-import write: the project (with its import hash),
   * one chapter document/revision per file, and the FTS rows commit together.
   */
  addImportedProject(
    scope: ProjectScope,
    input: AddImportedProjectInput,
  ): {
    project: ProjectRecord;
    documents: DocumentWithCurrent[];
  };
  dropProject(scope: ProjectScope, projectId: string): void;
}
