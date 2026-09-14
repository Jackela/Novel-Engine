import type { StudioBeatStore } from "./beat_store.js";
import { pageLimit } from "./page_limit.js";
import type { ProjectScope } from "./studio_store.js";
import type { WritingStatsHistory } from "./writing_stats.js";

/** Persistence-neutral row shape handed to the application layer. */
interface DocumentRecord {
  id: string;
  projectId: string;
  kind: string;
  title: string;
  position: number;
  /** The owning volume of a chapter; documents outside volumes stay null. */
  volumeId: string | null;
  /** The stored outline-beat reference; readers resolve it, dangling → unlinked. */
  beatRef: string | null;
  /**
   * Stored lore-alias JSON (#315, a `string[]`): document-level prompt keys
   * that must survive metadata-replacing revision writes.
   */
  loreAliasesJson: string;
  /**
   * Lore-entry lifecycle status (#444, ADR-0006): a closed `LoreStatus`
   * value for character/world documents; other kinds keep the `draft`
   * default and ignore it.
   */
  loreStatus: string;
  currentRevisionId: string | null;
  createdAt: Date;
  updatedAt: Date;
}

export interface RevisionRecord {
  id: string;
  documentId: string;
  parentRevisionId: string | null;
  revisionNumber: number;
  contentMarkdown: string;
  metadataJson: string;
  source: string;
  /** Nullable only while startup reconciliation upgrades an earlier database. */
  wordCount: number | null;
  createdAt: Date;
}

/** Lightweight immutable History item; body and metadata remain server authority. */
export interface RevisionSummaryRecord {
  id: string;
  documentId: string;
  parentRevisionId: string | null;
  revisionNumber: number;
  source: string;
  wordCount: number;
  createdAt: Date;
}

/** The validated row budget of one bounded document revision page. */
export type RevisionPageLimit = number & { readonly __revisionPageLimit: unique symbol };

const MIN_REVISION_PAGE_LIMIT = 1;
const MAX_REVISION_PAGE_LIMIT = 100;

/** Validate and narrow a revision-page budget before persistence. */
export function revisionPageLimit(value: number): RevisionPageLimit {
  return pageLimit<RevisionPageLimit>(value, {
    min: MIN_REVISION_PAGE_LIMIT,
    max: MAX_REVISION_PAGE_LIMIT,
    subject: "Revision",
  });
}

/** Persistence-neutral exclusive position in `(revision_number DESC, id DESC)` order. */
export interface RevisionPageCursor {
  readonly revisionNumber: number;
  readonly id: string;
}

export interface RevisionPageInput {
  readonly limit: RevisionPageLimit;
  readonly cursor?: RevisionPageCursor | undefined;
}

export interface RevisionSummaryPage {
  readonly revisions: RevisionSummaryRecord[];
  readonly nextCursor: RevisionPageCursor | null;
}

/** A document together with its current revision, the list/save/read shape. */
export interface DocumentWithCurrent extends DocumentRecord {
  currentRevision: RevisionRecord | null;
}

/** One full-text hit: the document id, its title, and a plain-text excerpt. */
export interface DocumentMatchRecord {
  documentId: string;
  title: string;
  excerpt: string;
}

export interface AddDocumentInput {
  kind: string;
  title: string;
  contentMarkdown: string;
  position: number;
  /** Chapters must name their volume; other kinds stay null. */
  volumeId: string | null;
  metadataJson: string;
  now: Date;
}

export interface AdvanceDocumentInput {
  contentMarkdown: string;
  baseRevisionId: string | null;
  title: string | null;
  metadataJson: string;
  source: string;
  now: Date;
}

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
  /**
   * Appends one immutable revision and moves current to it. `input.baseRevisionId`
   * must match the document's current revision id; a mismatch throws
   * `RevisionConflictError` carrying that `currentRevisionId` (rendered as
   * the 409 revision-conflict envelope) and writes nothing.
   */
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
   * The bounded revision-and-structure read the writing-statistics
   * aggregation folds (#653): every revision's stats evidence plus the
   * chapter documents' current word counts.
   */
  readWritingStatsHistory(scope: ProjectScope, projectId: string): WritingStatsHistory;

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
