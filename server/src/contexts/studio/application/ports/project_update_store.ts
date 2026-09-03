import type { ProjectRecord, ProjectScope } from "./studio_store.js";

/** Present properties are replaced; omitted properties remain stored unchanged. */
export interface ProjectUpdateInput {
  readonly title?: string | undefined;
  readonly description?: string | undefined;
  readonly settingsJson?: string | undefined;
  readonly now: Date;
}

/** Owner-scoped atomic Project scalar mutation. */
export interface ProjectUpdateStore {
  updateProject(scope: ProjectScope, projectId: string, input: ProjectUpdateInput): ProjectRecord;
}
