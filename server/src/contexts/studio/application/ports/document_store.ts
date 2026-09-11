import type { StudioBeatStore } from "./beat_store.js";
import type {
  AddDocumentInput,
  AdvanceDocumentInput,
  DocumentMatchRecord,
  DocumentWithCurrent,
  ProjectScope,
  RevisionPageInput,
  RevisionRecord,
  RevisionSummaryPage,
} from "./studio_store.js";

/**
 * Document-port of the authoring core: documents, their immutable revision
 * history, and the project FTS5 search surface. Every mutation keeps the
 * relational rows and the FTS index in one transaction; the Drizzle part
 * implements the port in infrastructure. Beat association (#313) extends the
 * same part, so its focused port composes here.
 */
export interface DocumentStore extends StudioBeatStore {
  findDocuments(scope: ProjectScope, projectId: string): DocumentWithCurrent[];
  findDocument(scope: ProjectScope, projectId: string, documentId: string): DocumentWithCurrent;
  readCurrentDocument(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
  ): DocumentWithCurrent;
  addDocument(scope: ProjectScope, projectId: string, input: AddDocumentInput): DocumentWithCurrent;
  advanceDocument(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    input: AdvanceDocumentInput,
  ): DocumentWithCurrent;
  dropDocument(scope: ProjectScope, projectId: string, documentId: string): void;
  /** Tail position for a kind; chapters position within their target volume. */
  nextPosition(
    scope: ProjectScope,
    projectId: string,
    kind: string,
    volumeId?: string | null,
  ): number;

  findRevisionSummaries(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    input: RevisionPageInput,
  ): RevisionSummaryPage;
  findRevision(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    revisionId: string,
  ): RevisionRecord;

  /**
   * Run a pre-reduced MATCH expression against the project's FTS index.
   * The expression must come from `buildFtsMatchQuery`; the store never
   * reduces raw user input itself.
   */
  matchProjectDocuments(
    scope: ProjectScope,
    projectId: string,
    matchQuery: string,
  ): DocumentMatchRecord[];
}
