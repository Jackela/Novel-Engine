import type { Principal } from "../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import { isDocumentKind } from "../domain/kinds.js";
import { assertSerializedCapacity } from "../domain/structure_capacity.js";
import { buildFtsLocateTerm, buildFtsMatchQuery } from "./fts_match_query.js";
import { documentMatchPayload, documentPayload, dumpJson } from "./payloads.js";
import type { DocumentMatchPageInput, DocumentStore } from "./ports/document_store.js";
import type { ProjectScope } from "./ports/studio_store.js";
import { scopeForPrincipal } from "./ports/studio_store.js";
import type { StudioVolumeStore } from "./ports/volume_store.js";
import { documentSummaryPayload } from "./project_shell_payloads.js";

/**
 * Conflict-checked document saves: the base revision decides between minting
 * the next immutable revision (advancing the document atomically) and a
 * revision conflict that carries the current revision id.
 */
export class DocumentService {
  private readonly documents: DocumentStore;
  private readonly volumes: StudioVolumeStore;
  private readonly now: () => Date;

  constructor(
    documents: DocumentStore,
    volumes: StudioVolumeStore,
    now: () => Date = () => new Date(),
  ) {
    this.documents = documents;
    this.volumes = volumes;
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
      input.kind === "chapter" ? resolveFirstVolumeId(this.volumes, scope, projectId) : null;
    const position =
      input.position === undefined || input.position === null
        ? this.documents.nextPosition(scope, projectId, input.kind, targetVolumeId)
        : input.position;
    const metadataJson = dumpJson(input.metadata ?? {});
    assertSerializedCapacity("document_metadata_bytes", metadataJson);
    return documentPayload(
      this.documents.addDocument(scope, projectId, {
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
      this.documents.readCurrentDocument(scopeForPrincipal(principal), projectId, documentId),
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
      /** The editor's autosave path (#DR-047); other writers leave it unset. */
      autosave?: boolean | undefined;
    },
  ): Record<string, unknown> {
    const title =
      input.title !== undefined && input.title !== null && input.title.trim() !== ""
        ? input.title.trim()
        : null;
    const metadataJson = dumpJson(input.metadata ?? {});
    assertSerializedCapacity("document_metadata_bytes", metadataJson);
    return documentPayload(
      this.documents.advanceDocument(scopeForPrincipal(principal), projectId, documentId, {
        contentMarkdown: input.contentMarkdown,
        baseRevisionId: input.baseRevisionId,
        title,
        metadataJson,
        source: input.source ?? "author",
        autosave: input.autosave,
        now: this.now(),
      }),
    );
  }

  removeDocument(principal: Principal, projectId: string, documentId: string): void {
    this.documents.dropDocument(scopeForPrincipal(principal), projectId, documentId);
  }

  /**
   * Project-scoped full-text query over titles and current content (DR-029):
   * raw input reduces to safe quoted tokens first; an irreducible query
   * answers an empty page with an honest zero total and no next page.
   * Otherwise the store returns one bounded page plus the project's total
   * match count, and every result carries the first reduced element as the
   * UI's locate term (never a fabricated one).
   */
  queryProjectDocuments(
    principal: Principal,
    projectId: string,
    query: string,
    page: DocumentMatchPageInput,
  ): Record<string, unknown> {
    const matchQuery = buildFtsMatchQuery(query);
    const locateTerm = buildFtsLocateTerm(query);
    // Both reduce the same input, so a null together is the irreducible case.
    if (matchQuery === null || locateTerm === null) {
      return { results: [], total: 0, next_offset: null };
    }
    const { matches, total } = this.documents.matchProjectDocuments(
      scopeForPrincipal(principal),
      projectId,
      matchQuery,
      page,
    );
    const results = matches.map((match) => documentMatchPayload(match, locateTerm));
    const consumed = page.offset + results.length;
    return { results, total, next_offset: consumed < total ? consumed : null };
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
    return this.volumes
      .renumberDocuments(scopeForPrincipal(principal), projectId, documentIds, this.now())
      .map(documentSummaryPayload);
  }
}

/** The project's first volume in reading order — the chapter-create target. */
function resolveFirstVolumeId(
  volumes: StudioVolumeStore,
  scope: ProjectScope,
  projectId: string,
): string {
  const [first] = volumes.findVolumes(scope, projectId);
  if (first === undefined) {
    throw new InvalidOperationError("A project must keep at least one volume.");
  }
  return first.id;
}
