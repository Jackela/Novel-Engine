import type { Principal } from "../../../shared/application/ports/auth.js";
import type { DocumentService } from "./document_service.js";
import type { RevisionPayload, RevisionSummaryPayload } from "./payload_schemas/revision.js";
import { revisionPayload, revisionSummaryPayload, safeLoadJson } from "./payloads.js";
import type {
  DocumentStore,
  RevisionPageCursor,
  RevisionPageInput,
} from "./ports/document_store.js";
import { scopeForPrincipal } from "./ports/studio_store.js";

interface RevisionHistoryPage {
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

  /**
   * One immutable revision body, owner-scoped exactly like the history list
   * and restore reads. A wrong-owner, wrong-document, or missing id throws
   * `NotFoundError`; the read never writes.
   */
  documentRevision(
    principal: Principal,
    projectId: string,
    documentId: string,
    revisionId: string,
  ): RevisionPayload {
    const revision = this.store.findRevision(
      scopeForPrincipal(principal),
      projectId,
      documentId,
      revisionId,
    );
    return revisionPayload(revision);
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
