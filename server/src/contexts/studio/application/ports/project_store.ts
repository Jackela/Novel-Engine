import type { ProjectCatalogStore } from "./project_catalog_store.js";
import type { ProjectShellRecord } from "./project_shell_records.js";
import type { ProjectUpdateStore } from "./project_update_store.js";
import type {
  AddImportedProjectInput,
  AddProjectInput,
  DocumentWithCurrent,
  ProjectRecord,
  ProjectScope,
} from "./studio_store.js";

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
