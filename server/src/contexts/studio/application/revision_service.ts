import type { Principal } from "../../../shared/application/ports/auth.js";
import type { DocumentService } from "./document_service.js";
import type { RevisionSummaryPayload } from "./payload_schemas/revision.js";
import { revisionSummaryPayload, safeLoadJson } from "./payloads.js";
import type { DocumentStore } from "./ports/document_store.js";
import {
  type RevisionPageCursor,
  type RevisionPageInput,
  scopeForPrincipal,
} from "./ports/studio_store.js";

export interface RevisionHistoryPage {
  readonly revisions: RevisionSummaryPayload[];
  readonly nextCursor: RevisionPageCursor | null;
}

/**
 * Revision history and restore. Restores never mutate history: the historic
 * revision is replayed into a brand-new revision with the server-assigned
 * source "restore".
 */
export class RevisionService {
  private readonly store: DocumentStore;
  private readonly documents: DocumentService;

  constructor(store: DocumentStore, documents: DocumentService) {
    this.store = store;
    this.documents = documents;
  }

  documentRevisions(
    principal: Principal,
    projectId: string,
    documentId: string,
    input: RevisionPageInput,
  ): RevisionHistoryPage {
    const page = this.store.findRevisionSummaries(
      scopeForPrincipal(principal),
      projectId,
      documentId,
      input,
    );
    return {
      revisions: page.revisions.map((revision) => revisionSummaryPayload(revision)),
      nextCursor: page.nextCursor,
    };
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
