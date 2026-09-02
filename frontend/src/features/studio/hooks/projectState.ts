import type { DocumentSummary, Project, StudioDocument } from "@/app/types/studio";

export function summarizeDocument(document: StudioDocument): DocumentSummary {
  const { content_markdown: _content, metadata: _metadata, ...summary } = document;
  return summary;
}

/** Merge one document result without letting a stale aggregate replace its siblings. */
export function mergeProjectDocument(project: Project, document: StudioDocument): Project {
  const documents = project.documents;
  if (!documents.some((candidate) => candidate.id === document.id)) return project;
  return {
    ...project,
    documents: documents.map((candidate) =>
      candidate.id === document.id ? summarizeDocument(document) : candidate,
    ),
  };
}

/** Apply only the positions owned by a reorder response. */
export function mergeProjectDocumentOrder(
  project: Project,
  orderedDocuments: readonly DocumentSummary[],
): Project {
  const currentById = new Map(project.documents.map((document) => [document.id, document]));
  const orderedIds = new Set(orderedDocuments.map((document) => document.id));
  const reordered = orderedDocuments.flatMap((ordered) => {
    const current = currentById.get(ordered.id);
    return current ? [{ ...current, position: ordered.position }] : [];
  });
  const remaining = project.documents.filter((document) => !orderedIds.has(document.id));
  return { ...project, documents: [...reordered, ...remaining] };
}

/** Apply only fields owned by the project-settings mutation. */
export function mergeProjectSettings(project: Project, updated: Project): Project {
  return {
    ...project,
    title: updated.title,
    description: updated.description,
    settings: updated.settings,
    updated_at: updated.updated_at > project.updated_at ? updated.updated_at : project.updated_at,
  };
}
