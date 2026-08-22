import type { Principal } from "../../../shared/application/ports/auth.js";
import type { DocumentService } from "./document_service.js";
import { revisionPayload, safeLoadJson } from "./payloads.js";
import { type StudioStore, scopeForPrincipal } from "./ports/studio_store.js";

/**
 * Revision history and restore. Restores never mutate history: the historic
 * revision is replayed into a brand-new revision with the server-assigned
 * source "restore".
 */
export class RevisionService {
  private readonly store: StudioStore;
  private readonly documents: DocumentService;

  constructor(store: StudioStore, documents: DocumentService) {
    this.store = store;
    this.documents = documents;
  }

  documentRevisions(
    principal: Principal,
    projectId: string,
    documentId: string,
  ): Record<string, unknown>[] {
    return this.store
      .findRevisions(scopeForPrincipal(principal), projectId, documentId)
      .map((revision) => revisionPayload(revision));
  }

  replayRevision(
    principal: Principal,
    projectId: string,
    documentId: string,
    revisionId: string,
    baseRevisionId: string | null,
  ): Record<string, unknown> {
    const revision = this.store.findRevision(
      scopeForPrincipal(principal),
      projectId,
      documentId,
      revisionId,
    );
    const metadata = safeLoadJson(revision.metadataJson);
    return this.documents.storeDocument(principal, projectId, documentId, {
      contentMarkdown: revision.contentMarkdown,
      baseRevisionId,
      metadata: { ...metadata, restored_from: revisionId },
      source: "restore",
    });
  }
}
