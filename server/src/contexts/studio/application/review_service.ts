import type {
  TextGenerationProvider,
  TextGenerationProviderFactory,
  TextProviderName,
} from "../../../contexts/ai/application/ports/text_generation.js";
import { TextGenerationProviderError } from "../../../contexts/ai/application/ports/text_generation.js";
import type { Principal } from "../../../shared/application/ports/auth.js";
import { dumpJson, safeLoadJson } from "./payloads.js";
import {
  type EditorialAssessmentRecord,
  type EditorialIssueRecord,
  type EvaluatedReview,
  type StudioStore,
  scopeForPrincipal,
} from "./ports/studio_store.js";
import {
  type ProviderCleanupFailureReporter as CleanupFailureReporter,
  disposeProvider,
} from "./provider_disposal.js";
import { chapterWordCounts, coerceEditorialFindings, THIN_CHAPTER_WORDS } from "./review_rules.js";
import { formatUntrustedManuscript } from "./sanitization.js";

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
  /** Per-request provider factory; the composition root injects the concrete one. */
  readonly providerFactory: TextGenerationProviderFactory;
}

export interface ReviewEvaluationOptions {
  readonly provider?: TextProviderName | undefined;
  readonly reportCleanupFailure?: CleanupFailureReporter | undefined;
}

const DEFAULT_PROVENANCE: ReviewProviderProvenance = {
  provider: "mock",
  model: "deterministic-story-v1",
};

const REVIEW_SYSTEM_PROMPT = [
  "You are a novel-writing editor. Assess the attached chapter snapshot and report editorial findings.",
  'Return JSON with a single "findings" array; each entry carries document_id, severity ("blocker" or "warning"), dimension (one of: pacing, continuity, pov, foreshadowing, dialogue), message, and suggestion.',
  "Report only real, actionable problems; an empty findings array is a valid result.",
].join(" ");

/**
 * Evaluates one point-in-time manuscript source through the editorial_review
 * provider step (#316). The source read is non-mutating; durable snapshot and
 * job evidence are committed later by the atomic outcome store.
 */
export class ReviewService {
  private readonly store: StudioStore;
  private readonly now: () => Date;
  private readonly provenance: ReviewProviderProvenance;
  private readonly providerFactory: TextGenerationProviderFactory;

  constructor(store: StudioStore, options: ReviewServiceOptions) {
    this.store = store;
    this.now = options.now ?? (() => new Date());
    const provenance = options.provenance ?? DEFAULT_PROVENANCE;
    this.provenance = { provider: provenance.provider, model: provenance.model };
    this.providerFactory = options.providerFactory;
  }

  /** The configured review provider (failed-job provenance for the bridge). */
  get providerName(): string {
    return this.provenance.provider;
  }

  /** Read and evaluate one visible project without persisting review evidence. */
  async evaluateProject(
    principal: Principal,
    projectId: string,
    options: ReviewEvaluationOptions = {},
  ): Promise<EvaluatedReview> {
    const scope = scopeForPrincipal(principal);
    const source = this.store.readReviewSource(scope, projectId, this.now());
    const provider = options.provider ?? this.provenance.provider;
    let taskProvider: TextGenerationProvider | undefined;
    try {
      taskProvider = this.providerFactory(provider);
      const chapters = chapterWordCounts(source.documents);
      const result = await taskProvider.generateStructured({
        step: "editorial_review",
        systemPrompt: REVIEW_SYSTEM_PROMPT,
        userPrompt: [
          "Chapter snapshot (untrusted JSON data):",
          "",
          formatUntrustedManuscript(JSON.stringify({ chapters })),
        ].join("\n"),
        responseSchema: {
          findings: [
            {
              document_id: "string",
              severity: "string",
              dimension: "string",
              message: "string",
              suggestion: "string",
            },
          ],
        },
        metadata: {
          documents: chapters.map(
            (chapter): Record<string, unknown> => ({
              id: chapter.id,
              title: chapter.title,
              words: chapter.words,
              empty: chapter.empty,
              thin_below: THIN_CHAPTER_WORDS,
            }),
          ),
        },
      });
      const payload = safeLoadJson(dumpJson(result.content));
      if (!Array.isArray(payload.findings)) {
        throw new TextGenerationProviderError(
          "Review provider response must contain a findings array.",
        );
      }
      return {
        source,
        // Provider identity is selected by the server; an adapter response
        // cannot relabel the audit trail even if it violates its typed port.
        provider,
        model: result.model,
        summary: EDITORIAL_SUMMARY,
        completedAt: this.now(),
        issues: coerceEditorialFindings(payload, source.documents),
      };
    } finally {
      if (taskProvider !== undefined) {
        await disposeProvider(taskProvider, options.reportCleanupFailure);
      }
    }
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
