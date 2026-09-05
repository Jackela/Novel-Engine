import type {
  DocumentSummary,
  LoreStatus,
  Project,
  ProjectListItem,
  StudioDocument,
} from "@/app/types/studio";

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
export function mergeProjectSettings(project: Project, updated: ProjectListItem): Project {
  return {
    ...project,
    title: updated.title,
    description: updated.description,
    settings: updated.settings,
    updated_at: updated.updated_at > project.updated_at ? updated.updated_at : project.updated_at,
  };
}

/** One narrow summary field a revision-free command owns exclusively (#466). */
export type NarrowSummaryPatch =
  | { readonly field: "lore_status"; readonly value: LoreStatus }
  | { readonly field: "beat_ref"; readonly value: string | null };

/** The project/Document/revision world a narrow command was issued against. */
export interface NarrowFieldCapture {
  readonly projectId: string;
  readonly documentId: string;
  /** Summary revision observed when the command was issued. */
  readonly revisionId: string;
}

/**
 * Patch exactly one narrow summary field, and only while the captured
 * project/Document identity still owns the shell row at the same revision
 * (task 3.4): an older-revision response never overwrites newer authority.
 */
export function mergeProjectNarrowField(
  project: Project,
  capture: NarrowFieldCapture,
  patch: NarrowSummaryPatch,
): Project {
  if (project.id !== capture.projectId) return project;
  const row = project.documents.find((document) => document.id === capture.documentId);
  if (row === undefined || row.current_revision_id !== capture.revisionId) return project;
  return {
    ...project,
    documents: project.documents.map((document) => {
      if (document.id !== capture.documentId) return document;
      return patch.field === "lore_status"
        ? { ...document, lore_status: patch.value }
        : { ...document, beat_ref: patch.value };
    }),
  };
}
