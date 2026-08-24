import type { TextProviderName } from "../../../contexts/ai/application/ports/text_generation.js";
import type { Principal } from "../../../shared/application/ports/auth.js";
import {
  type EditorialAssessmentRecord,
  type EditorialIssueRecord,
  type StudioStore,
  scopeForPrincipal,
} from "./ports/studio_store.js";
import { inspectSnapshotDocuments } from "./review_rules.js";

/** The adjudicated summary of a deterministic, non-mutating editorial pass. */
export const EDITORIAL_SUMMARY = "Editorial checks completed without modifying the manuscript.";

/** Server-owned provenance; callers never supply a provider model. */
export interface ReviewProviderProvenance {
  readonly provider: TextProviderName;
  readonly model: string;
}

/** Stable application DTO, deliberately independent of database row shapes. */
export interface EditorialAssessmentIssue {
  readonly id: string;
  readonly documentId: string;
  readonly severity: string;
  readonly code: string;
  readonly message: string;
  readonly suggestion: string;
  readonly evidence: Record<string, unknown>;
}

/** Snapshot-bound review result ready for a later HTTP mapper. */
export interface EditorialAssessment {
  readonly id: string;
  readonly projectId: string;
  readonly snapshotId: string;
  readonly provider: string;
  readonly model: string;
  readonly summary: string;
  readonly createdAt: Date;
  readonly issues: readonly EditorialAssessmentIssue[];
}

export interface ReviewServiceOptions {
  readonly now?: (() => Date) | undefined;
  readonly provenance?: ReviewProviderProvenance | undefined;
}

const DEFAULT_PROVENANCE: ReviewProviderProvenance = {
  provider: "mock",
  model: "deterministic-story-v1",
};

/**
 * Evaluates immutable manuscript snapshots. The service never passes a
 * client-supplied model through to persistence and never edits live content.
 */
export class ReviewService {
  private readonly store: StudioStore;
  private readonly now: () => Date;
  private readonly provenance: ReviewProviderProvenance;

  constructor(store: StudioStore, options: ReviewServiceOptions = {}) {
    this.store = store;
    this.now = options.now ?? (() => new Date());
    const provenance = options.provenance ?? DEFAULT_PROVENANCE;
    this.provenance = { provider: provenance.provider, model: provenance.model };
  }

  /** Capture and assess the current revisions of one visible project. */
  evaluateProject(principal: Principal, projectId: string): EditorialAssessment {
    const recorded = this.store.recordSnapshotReview(scopeForPrincipal(principal), projectId, {
      provider: this.provenance.provider,
      model: this.provenance.model,
      summary: EDITORIAL_SUMMARY,
      now: this.now(),
      evaluator: (documents) =>
        inspectSnapshotDocuments(
          documents.map((document) => ({
            id: document.documentId,
            kind: document.kind,
            title: document.title,
            contentMarkdown: document.contentMarkdown,
          })),
        ),
    });
    return editorialAssessment(recorded);
  }

  /** List stored assessments without reevaluating newer live revisions. */
  listEditorialAssessments(principal: Principal, projectId: string): EditorialAssessment[] {
    return this.store
      .listEditorialAssessments(scopeForPrincipal(principal), projectId)
      .map(editorialAssessment);
  }
}

function editorialAssessment(record: EditorialAssessmentRecord): EditorialAssessment {
  return {
    id: record.id,
    projectId: record.projectId,
    snapshotId: record.snapshotId,
    provider: record.provider,
    model: record.model,
    summary: record.summary,
    createdAt: record.createdAt,
    issues: record.issues.map(editorialIssue),
  };
}

function editorialIssue(record: EditorialIssueRecord): EditorialAssessmentIssue {
  return {
    id: record.id,
    documentId: record.documentId,
    severity: record.severity,
    code: record.code,
    message: record.message,
    suggestion: record.suggestion,
    evidence: { ...record.evidence },
  };
}
