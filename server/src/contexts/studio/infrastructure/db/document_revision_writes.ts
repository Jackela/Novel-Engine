import { eq } from "drizzle-orm";

import type {
  AdvanceDocumentInput,
  DocumentWithCurrent,
  ProjectScope,
} from "../../application/ports/studio_store.js";
import { NotFoundError, RevisionConflictError } from "../../domain/exceptions.js";
import { refreshDocumentIndex } from "./document_search.js";
import { documentRevisions, documents, projects } from "./schema.js";
import { insertRevision, scopedDocument, scopedProject, type Tx } from "./studio_query_helpers.js";

/**
 * The sole transaction-owned implementation of an immutable revision advance.
 * Ordinary saves wrap it in their own transaction; compound workflows can
 * compose it with their other writes without opening a second transaction.
 */
export function advanceDocumentInTransaction(
  tx: Tx,
  scope: ProjectScope,
  projectId: string,
  documentId: string,
  input: AdvanceDocumentInput,
): DocumentWithCurrent {
  const project = scopedProject(tx, scope, projectId);
  const document = scopedDocument(tx, scope, projectId, documentId);
  if (document.currentRevisionId !== input.baseRevisionId) {
    throw new RevisionConflictError(document.currentRevisionId);
  }
  const current = tx
    .select()
    .from(documentRevisions)
    .where(eq(documentRevisions.id, document.currentRevisionId ?? ""))
    .get();
  if (current === undefined) {
    throw new NotFoundError("Current revision not found.");
  }
  const revision = insertRevision(tx, {
    documentId: document.id,
    parentRevisionId: document.currentRevisionId,
    revisionNumber: current.revisionNumber + 1,
    contentMarkdown: input.contentMarkdown,
    metadataJson: input.metadataJson,
    source: input.source,
    now: input.now,
  });
  const title = input.title ?? document.title;
  tx.update(documents)
    .set({ currentRevisionId: revision.id, title, updatedAt: input.now })
    .where(eq(documents.id, document.id))
    .run();
  refreshDocumentIndex(tx, {
    documentId: document.id,
    projectId: project.id,
    title,
    content: input.contentMarkdown,
  });
  tx.update(projects).set({ updatedAt: input.now }).where(eq(projects.id, project.id)).run();
  return {
    ...document,
    title,
    currentRevisionId: revision.id,
    updatedAt: input.now,
    currentRevision: revision,
  };
}
