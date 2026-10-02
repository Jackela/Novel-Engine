import { api } from "@/app/api";
import type { StudioDocument } from "@/app/types/studio";

/** Saves one Draft body as a new immutable Revision on the server. */
export function saveDocumentDraft(
  projectId: string,
  document: StudioDocument,
  content: string,
  title: string,
  baseRevisionId: string,
): Promise<StudioDocument> {
  return api.saveDocument(projectId, document.id, {
    content_markdown: content,
    base_revision_id: baseRevisionId,
    title,
  });
}

/** Restores an immutable Revision as the Document's next current revision. */
export function restoreDocumentRevision(
  projectId: string,
  document: StudioDocument,
  revisionId: string,
  baseRevisionId: string,
): Promise<StudioDocument> {
  return api.restoreRevision(projectId, document.id, revisionId, baseRevisionId);
}

/** Reads the latest server state of one Document. */
export async function loadLatestDocument(
  projectId: string,
  documentId: string,
  signal?: AbortSignal,
): Promise<StudioDocument> {
  return api.document(projectId, documentId, { signal });
}
