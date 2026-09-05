import type { ProjectRecord, ProjectScope } from "./studio_store.js";

interface OptionalProjectUpdateFields {
  readonly title?: string | undefined;
  readonly description?: string | undefined;
  readonly settingsJson?: string | undefined;
}

/** At least one present property is replaced; omitted properties remain stored unchanged. */
export type ProjectUpdateInput = { readonly now: Date } & (
  | (OptionalProjectUpdateFields & { readonly title: string })
  | (OptionalProjectUpdateFields & { readonly description: string })
  | (OptionalProjectUpdateFields & { readonly settingsJson: string })
);

/** Owner-scoped atomic Project scalar mutation. */
export interface ProjectUpdateStore {
  updateProject(scope: ProjectScope, projectId: string, input: ProjectUpdateInput): ProjectRecord;
}
