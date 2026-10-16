import type { Project, StudioDocument } from "@/app/types/studio";
import { summarizeDocument } from "./projectState";

/**
 * Adds one accepted creation to its live project shell. A stale project,
 * mismatched response, or repeated notification leaves the shell unchanged;
 * an existing summary is never overwritten by an older creation response.
 */
export function mergeCreatedProjectDocument(
  project: Project | null,
  projectId: string,
  document: StudioDocument,
): Project | null {
  if (
    project?.id !== projectId ||
    document.project_id !== projectId ||
    project.documents.some((entry) => entry.id === document.id)
  )
    return project;
  return { ...project, documents: [...project.documents, summarizeDocument(document)] };
}
