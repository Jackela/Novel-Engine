import type { Principal } from "../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import { isDocumentKind } from "../domain/kinds.js";
import { assertSerializedCapacity } from "../domain/structure_capacity.js";
import { buildFtsMatchQuery } from "./fts_match_query.js";
import { documentMatchPayload, documentPayload, dumpJson } from "./payloads.js";
import type { ProjectScope } from "./ports/studio_store.js";
import { type StudioStore, scopeForPrincipal } from "./ports/studio_store.js";
import { documentSummaryPayload } from "./project_shell_payloads.js";

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
    // Chapters belong to exactly one volume (ADR-0005); an unassigned create
    // lands at the tail of the project's first volume in reading order.
    const targetVolumeId =
      input.kind === "chapter" ? resolveFirstVolumeId(this.store, scope, projectId) : null;
    const position =
      input.position === undefined || input.position === null
        ? this.store.nextPosition(scope, projectId, input.kind, targetVolumeId)
        : input.position;
    const metadataJson = dumpJson(input.metadata ?? {});
    assertSerializedCapacity("document_metadata_bytes", metadataJson);
    return documentPayload(
      this.store.addDocument(scope, projectId, {
        kind: input.kind,
        title: input.title,
        contentMarkdown: input.contentMarkdown ?? "",
        position,
        volumeId: targetVolumeId,
        metadataJson,
        now: this.now(),
      }),
    );
  }

  currentDocument(
    principal: Principal,
    projectId: string,
    documentId: string,
  ): Record<string, unknown> {
    return documentPayload(
      this.store.readCurrentDocument(scopeForPrincipal(principal), projectId, documentId),
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
    const metadataJson = dumpJson(input.metadata ?? {});
    assertSerializedCapacity("document_metadata_bytes", metadataJson);
    return documentPayload(
      this.store.advanceDocument(scopeForPrincipal(principal), projectId, documentId, {
        contentMarkdown: input.contentMarkdown,
        baseRevisionId: input.baseRevisionId,
        title,
        metadataJson,
        source: input.source ?? "author",
        now: this.now(),
      }),
    );
  }

  removeDocument(principal: Principal, projectId: string, documentId: string): void {
    this.store.dropDocument(scopeForPrincipal(principal), projectId, documentId);
  }

  /**
   * Project-scoped full-text query over titles and current content. Raw
   * input reduces to safe quoted tokens first; an irreducible query
   * answers empty without touching the index.
   */
  queryProjectDocuments(
    principal: Principal,
    projectId: string,
    query: string,
  ): Record<string, unknown>[] {
    const matchQuery = buildFtsMatchQuery(query);
    if (matchQuery === null) {
      return [];
    }
    return this.store
      .matchProjectDocuments(scopeForPrincipal(principal), projectId, matchQuery)
      .map((match) => documentMatchPayload(match));
  }

  /**
   * Whole-set reorder projected onto volumes by the store; the request must
   * name every project document exactly once.
   */
  reorderProjectDocuments(
    principal: Principal,
    projectId: string,
    documentIds: string[],
  ): Record<string, unknown>[] {
    return this.store
      .renumberDocuments(scopeForPrincipal(principal), projectId, documentIds, this.now())
      .map(documentSummaryPayload);
  }
}

/** The project's first volume in reading order — the chapter-create target. */
function resolveFirstVolumeId(store: StudioStore, scope: ProjectScope, projectId: string): string {
  const [first] = store.findVolumes(scope, projectId);
  if (first === undefined) {
    throw new InvalidOperationError("A project must keep at least one volume.");
  }
  return first.id;
}
