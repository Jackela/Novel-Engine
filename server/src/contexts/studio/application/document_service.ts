import type { Principal } from "../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import { isDocumentKind } from "../domain/kinds.js";
import { documentPayload, dumpJson } from "./payloads.js";
import {
  type DocumentWithCurrent,
  type StudioStore,
  scopeForPrincipal,
} from "./ports/studio_store.js";

/**
 * Conflict-checked document saves: the base revision decides between minting
 * the next immutable revision (advancing the document atomically) and a
 * revision conflict that carries the current revision id.
 */
export class DocumentService {
  private readonly store: StudioStore;
  private readonly now: () => Date;

  constructor(store: StudioStore, now: () => Date = () => new Date()) {
    this.store = store;
    this.now = now;
  }

  newDocument(
    principal: Principal,
    projectId: string,
    input: {
      kind: string;
      title: string;
      contentMarkdown?: string | undefined;
      position?: number | null | undefined;
      metadata?: Record<string, unknown> | undefined;
    },
  ): Record<string, unknown> {
    if (!isDocumentKind(input.kind)) {
      throw new InvalidOperationError(`Unsupported document kind: ${input.kind}`);
    }
    const scope = scopeForPrincipal(principal);
    const position =
      input.position === undefined || input.position === null
        ? this.store.nextPosition(scope, projectId, input.kind)
        : input.position;
    return documentPayload(
      this.store.addDocument(scope, projectId, {
        kind: input.kind,
        title: input.title,
        contentMarkdown: input.contentMarkdown ?? "",
        position,
        metadataJson: dumpJson(input.metadata ?? {}),
        now: this.now(),
      }),
    );
  }

  documentById(
    principal: Principal,
    projectId: string,
    documentId: string,
  ): Record<string, unknown> {
    return documentPayload(
      this.store.findDocument(scopeForPrincipal(principal), projectId, documentId),
    );
  }

  /**
   * Save against a base revision: a fresh base creates revision n+1 with the
   * current revision as parent and advances the document in one operation;
   * a stale base is rejected without creating anything.
   */
  storeDocument(
    principal: Principal,
    projectId: string,
    documentId: string,
    input: {
      contentMarkdown: string;
      baseRevisionId: string | null;
      title?: string | null | undefined;
      metadata?: Record<string, unknown> | undefined;
      source?: string | undefined;
    },
  ): Record<string, unknown> {
    const title =
      input.title !== undefined && input.title !== null && input.title.trim() !== ""
        ? input.title.trim()
        : null;
    return documentPayload(
      this.store.advanceDocument(scopeForPrincipal(principal), projectId, documentId, {
        contentMarkdown: input.contentMarkdown,
        baseRevisionId: input.baseRevisionId,
        title,
        metadataJson: dumpJson(input.metadata ?? {}),
        source: input.source ?? "author",
        now: this.now(),
      }),
    );
  }

  removeDocument(principal: Principal, projectId: string, documentId: string): void {
    this.store.dropDocument(scopeForPrincipal(principal), projectId, documentId);
  }

  /**
   * Whole-set reorder: the request must name every project document exactly
   * once; positions are renumbered 1..n in the requested order.
   */
  reorderProjectDocuments(
    principal: Principal,
    projectId: string,
    documentIds: string[],
  ): Record<string, unknown>[] {
    return this.store
      .renumberDocuments(scopeForPrincipal(principal), projectId, documentIds, this.now())
      .map((document: DocumentWithCurrent) => documentPayload(document));
  }
}
