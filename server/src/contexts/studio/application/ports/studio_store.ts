import type { Principal } from "../../../../shared/application/ports/auth.js";
import type {
  AddJobInput,
  AddUsageEventInput,
  JobRecord,
  MarkJobOutcomeInput,
} from "./job_records.js";

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
  createdAt: Date;
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
  JobEventRecord,
  JobRecord,
  MarkJobOutcomeInput,
} from "./job_records.js";

/** A document/revision pair frozen into an immutable review snapshot. */
export interface ReviewSnapshotDocument {
  /** The source document identifier, retained for finding-to-snapshot mapping. */
  documentId: string;
  snapshotDocumentId: string;
  revisionId: string;
  kind: string;
  title: string;
  contentMarkdown: string;
  metadataJson: string;
  position: number;
}

/** A pure evaluator's finding, before the adapter serializes its evidence. */
export interface EditorialIssueInput {
  documentId: string;
  severity: string;
  code: string;
  message: string;
  suggestion: string;
  evidence: Record<string, unknown>;
}

/** One persisted editorial issue, returned without exposing database rows. */
export interface EditorialIssueRecord extends EditorialIssueInput {
  id: string;
  reviewId: string;
  snapshotDocumentId: string;
}

/** A snapshot-bound editorial assessment and its stably ordered issues. */
export interface EditorialAssessmentRecord {
  id: string;
  projectId: string;
  snapshotId: string;
  provider: string;
  model: string;
  summary: string;
  createdAt: Date;
  issues: EditorialIssueRecord[];
}

export interface CaptureReviewSnapshotInput {
  now: Date;
}

export interface RecordSnapshotReviewInput {
  snapshotId: string;
  provider: string;
  model: string;
  summary: string;
  now: Date;
  issues: readonly EditorialIssueInput[];
}

/**
 * Owner scoping of every project query: the single principal since #311
 * retired the guest.
 */
export interface ProjectScope {
  ownerId: string;
}

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
 * store implements it transactionally in infrastructure.
 */
export interface StudioStore {
  addProject(
    scope: ProjectScope,
    input: AddProjectInput,
  ): {
    project: ProjectRecord;
    documents: DocumentWithCurrent[];
  };
  findProjects(scope: ProjectScope): ProjectRecord[];
  findProject(scope: ProjectScope, projectId: string): ProjectRecord;
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
  ): DocumentWithCurrent[];
  nextPosition(scope: ProjectScope, projectId: string, kind: string): number;

  findRevisions(scope: ProjectScope, projectId: string, documentId: string): RevisionRecord[];
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

  addJob(scope: ProjectScope, input: AddJobInput): JobRecord;
  addUsageEvent(scope: ProjectScope, input: AddUsageEventInput): void;
  findJob(scope: ProjectScope, projectId: string, jobId: string): JobRecord;
  /**
   * The jobs audit trail, newest job first and each job's events newest
   * first — the OpenSpec listing contract for the synchronous jobs model.
   */
  collectProjectJobs(scope: ProjectScope, projectId: string): JobRecord[];
  /** Transition a persisted job and append its matching event atomically. */
  markJobOutcome(
    scope: ProjectScope,
    projectId: string,
    jobId: string,
    input: MarkJobOutcomeInput,
  ): JobRecord;
  setJobResult(
    scope: ProjectScope,
    projectId: string,
    jobId: string,
    resultJson: string,
    now: Date,
  ): JobRecord;

  /**
   * Freeze current document content before evaluating it; review history can
   * therefore never be rewritten by later author edits. The capture commits
   * on its own so the (asynchronous) evaluation can run against immutable
   * rows before the review record is persisted.
   */
  captureReviewSnapshot(
    scope: ProjectScope,
    projectId: string,
    input: CaptureReviewSnapshotInput,
  ): { snapshotId: string; documents: ReviewSnapshotDocument[] };
  recordSnapshotReview(
    scope: ProjectScope,
    projectId: string,
    input: RecordSnapshotReviewInput,
  ): EditorialAssessmentRecord;
  listEditorialAssessments(scope: ProjectScope, projectId: string): EditorialAssessmentRecord[];
}
