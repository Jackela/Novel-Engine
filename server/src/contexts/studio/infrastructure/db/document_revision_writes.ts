import { eq } from "drizzle-orm";
import type {
  AdvanceDocumentInput,
  DocumentWithCurrent,
} from "../../application/ports/document_store.js";
import type { RevisionPins } from "../../application/ports/revision_pins.js";
import type { ProjectScope } from "../../application/ports/studio_store.js";
import { NotFoundError, RevisionConflictError } from "../../domain/exceptions.js";
import { refreshDocumentIndex } from "./document_search.js";
import { isCollapsibleAutosavePredecessor, pruneRetainedRevisions } from "./revision_retention.js";
import { documentRevisions, documents, projects } from "./schema.js";
import { assertOutlineBeatCapacity } from "./structure_capacity_checks.js";
import { insertRevision, scopedDocument, scopedProject, type Tx } from "./studio_query_helpers.js";

/**
 * The sole transaction-owned implementation of an immutable revision advance.
 * Ordinary saves wrap it in their own transaction; compound workflows can
 * compose it with their other writes without opening a second transaction.
 *
 * Revision growth guards (#DR-047) apply to the editor's autosave path only
 * (`input.autosave`), never to restores, accepted proposals, or imports:
 *
 * - an author save whose body, metadata, and title already match the current
 *   revision writes nothing at all — no revision row, no FTS rewrite, no
 *   timestamps — and answers the current document state, so a repeated
 *   autosave is idempotent;
 * - an autosave folds an unreferenced author predecessor written inside the
 *   collapse window into the new revision (the predecessor is deleted, the
 *   new revision inherits its parent, so the lineage chain stays intact);
 * - an autosave prunes old unreferenced autosave revisions beyond the
 *   retention window and the newest-N floor.
 *
 * Snapshot-pinned revisions are immutable: the collapse decision and the
 * prune both refuse to touch a row a snapshot references.
 */
export function advanceDocumentInTransaction(
  tx: Tx,
  scope: ProjectScope,
  projectId: string,
  documentId: string,
  input: AdvanceDocumentInput,
  revisionPins?: RevisionPins,
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
    throw new NotFoundError(`Current revision not found: ${documentId}.`);
  }
  const title = input.title ?? document.title;
  if (
    input.source === "author" &&
    current.contentMarkdown === input.contentMarkdown &&
    current.metadataJson === input.metadataJson &&
    document.title === title
  ) {
    return { ...document, currentRevision: current };
  }
  // Every path that mints outline content (author saves, restores, accepted
  // AI proposals) funnels through this chokepoint, so the beat budget holds
  // for all of them before any revision row is written (#461).
  assertOutlineBeatCapacity(document.kind, input.contentMarkdown);
  const collapse =
    input.autosave === true &&
    isCollapsibleAutosavePredecessor(
      tx,
      {
        revisionId: current.id,
        parentRevisionId: current.parentRevisionId,
        source: current.source,
        createdAt: current.createdAt,
      },
      input.now,
      revisionPins,
    );
  const revision = insertRevision(tx, {
    documentId: document.id,
    parentRevisionId: collapse ? current.parentRevisionId : document.currentRevisionId,
    revisionNumber: current.revisionNumber + 1,
    contentMarkdown: input.contentMarkdown,
    metadataJson: input.metadataJson,
    source: input.source,
    now: input.now,
  });
  if (collapse) {
    tx.delete(documentRevisions).where(eq(documentRevisions.id, current.id)).run();
  }
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
  if (input.autosave === true) {
    pruneRetainedRevisions(
      tx,
      {
        documentId: document.id,
        currentRevisionId: revision.id,
        currentRevisionNumber: revision.revisionNumber,
        now: input.now,
      },
      revisionPins,
    );
  }
  return {
    ...document,
    title,
    currentRevisionId: revision.id,
    updatedAt: input.now,
    currentRevision: revision,
  };
}
