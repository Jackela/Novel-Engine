import type { Principal } from "../../../../shared/application/ports/auth.js";
import type { StudioBeatStore } from "./beat_store.js";
import type { StudioJobLedgerStore } from "./job_ledger_store.js";
import type { StudioLoreStore } from "./lore_store.js";
import type { DocumentSummaryRecord, ProjectShellRecord } from "./project_shell_records.js";
import type { ProposalAcceptanceStore } from "./proposal_acceptance_store.js";
import type { ProposalContextStore } from "./proposal_context_store.js";
import type { ReviewOutcomeStore } from "./review_outcome_store.js";
import type { StudioVolumeStore } from "./volume_store.js";

export type { DocumentSummaryRecord, ProjectShellRecord } from "./project_shell_records.js";

/** Persistence-neutral row shapes handed to the application layer. */
export interface ProjectRecord {
  id: string;
  ownerId: string;
  title: string;
  description: string;
  settingsJson: string;
  importHash: string | null;
  createdAt: Date;
  updatedAt: Date;
}

export interface DocumentRecord {
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

export const MIN_REVISION_PAGE_LIMIT = 1;
export const MAX_REVISION_PAGE_LIMIT = 100;

/** Validate and narrow a revision-page budget before persistence. */
export function revisionPageLimit(value: number): RevisionPageLimit {
  if (
    !Number.isInteger(value) ||
    value < MIN_REVISION_PAGE_LIMIT ||
    value > MAX_REVISION_PAGE_LIMIT
  ) {
    throw new RangeError(
      `Revision page limit must be an integer from ${MIN_REVISION_PAGE_LIMIT} through ${MAX_REVISION_PAGE_LIMIT}.`,
    );
  }
  return value as RevisionPageLimit;
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

/** Job-row shapes live in their own module (file-size split); re-exported. */
export type {
  AddJobInput,
  AddUsageEventInput,
  ClaimJobRetryInput,
  CompletedProposalUsageInput,
  CompleteJobWithUsageInput,
  JobEventRecord,
  JobRecord,
  JobRetryClaim,
  MarkJobOutcomeInput,
  RecordCompletedProposalJobInput,
} from "./job_records.js";

/** Review-outcome types live in their focused port module; re-exported here. */
export type {
  EditorialAssessmentRecord,
  EditorialIssueInput,
  EditorialIssueRecord,
  EvaluatedReview,
  ReviewCompletionRecord,
  ReviewSnapshotDocument,
  ReviewSource,
  ReviewSourceDocument,
} from "./review_outcome_store.js";

/**
 * Owner scoping of every project query: the single principal since #311
 * retired the guest.
 */
export interface ProjectScope {
  ownerId: string;
}

/** The aggregated usage-ledger types (#317, #384), shared with the HTTP surface. */
export type {
  ProjectUsageAggregate,
  ProjectUsageBreakdownEntry,
  ProjectUsageDailyBucket,
} from "./project_usage.js";

/** Derive the store scope from the authenticated owner principal. */
export function scopeForPrincipal(principal: Principal): ProjectScope {
  if (principal.ownerId === null) {
    throw new Error("A principal without an owner cannot scope studio data.");
  }
  return { ownerId: principal.ownerId };
}

export interface AddProjectInput {
  title: string;
  description: string;
  settingsJson: string;
  /** Seed document/revision written in the same transaction as the project. */
  seed: { kind: string; title: string; contentMarkdown: string; metadataJson: string } | null;
  now: Date;
}

/** One imported chapter: content plus its persisted metadata JSON. */
export interface ImportedChapterInput {
  contentMarkdown: string;
  metadataJson: string;
}

/**
 * The whole legacy-import write: the project row already carries its import
 * hash, and every chapter document/revision lands in the same transaction.
 */
export interface AddImportedProjectInput {
  title: string;
  description: string;
  settingsJson: string;
  importHash: string;
  chapters: ImportedChapterInput[];
  now: Date;
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
 * Persistence port of the authoring core. The application layer orchestrates
 * project, document, and revision behavior through this port; the Drizzle
 * store implements it transactionally in infrastructure. The volume surface
 * (ADR-0005) extends it from its own module, as do the beat association
 * (#313) and the lorebook aliases (#315).
 */
export interface StudioStore
  extends StudioVolumeStore,
    StudioBeatStore,
    StudioLoreStore,
    ProposalContextStore,
    ProposalAcceptanceStore,
    ReviewOutcomeStore,
    StudioJobLedgerStore {
  addProject(
    scope: ProjectScope,
    input: AddProjectInput,
  ): {
    project: ProjectRecord;
    documents: DocumentWithCurrent[];
  };
  findProjects(scope: ProjectScope): ProjectRecord[];
  findProject(scope: ProjectScope, projectId: string): ProjectRecord;
  readProjectShell(scope: ProjectScope, projectId: string): ProjectShellRecord;
  /** Existing project of this principal carrying the given import hash, if any. */
  findProjectByImportHash(scope: ProjectScope, importHash: string): ProjectRecord | null;
  /**
   * Transactional legacy-import write: the project (with its import hash),
   * one chapter document/revision per file, and the FTS rows commit together.
   */
  addImportedProject(
    scope: ProjectScope,
    input: AddImportedProjectInput,
  ): {
    project: ProjectRecord;
    documents: DocumentWithCurrent[];
  };
  dropProject(scope: ProjectScope, projectId: string): void;

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
  renumberDocuments(
    scope: ProjectScope,
    projectId: string,
    documentIds: string[],
    now: Date,
  ): DocumentSummaryRecord[];
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
