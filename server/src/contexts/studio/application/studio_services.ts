import { DocumentService } from "./document_service.js";
import type { StudioStore } from "./ports/studio_store.js";
import { ProjectService } from "./project_service.js";
import { RevisionService } from "./revision_service.js";

/** The per-capability service graph handed to the studio HTTP surface. */
export interface StudioServices {
  projects: ProjectService;
  documents: DocumentService;
  revisions: RevisionService;
}

export function createStudioServices(
  store: StudioStore,
  now: () => Date = () => new Date(),
): StudioServices {
  const documents = new DocumentService(store, now);
  return {
    projects: new ProjectService(store, now),
    documents,
    revisions: new RevisionService(store, documents),
  };
}
