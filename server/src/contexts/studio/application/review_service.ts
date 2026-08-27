import type {
  TextGenerationProvider,
  TextGenerationProviderFactory,
  TextProviderName,
} from "../../../contexts/ai/application/ports/text_generation.js";
import type { Principal } from "../../../shared/application/ports/auth.js";
import { dumpJson, safeLoadJson } from "./payloads.js";
import {
  type EditorialAssessmentRecord,
  type EditorialIssueRecord,
  type StudioStore,
  scopeForPrincipal,
} from "./ports/studio_store.js";
import { chapterWordCounts, coerceEditorialFindings } from "./review_rules.js";
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

const DEFAULT_PROVENANCE: ReviewProviderProvenance = {
  provider: "mock",
  model: "deterministic-story-v1",
};

const REVIEW_SYSTEM_PROMPT = [
  "You are a novel-writing editor. Assess the attached chapter snapshot and report editorial findings.",
  'Return JSON with a single "findings" array; each entry carries document_id, severity ("blocker" or "warning"), dimension (one of: pacing, continuity, pov, foreshadowing, dialogue), message, and suggestion.',
  "Report only real, actionable problems; an empty findings array is a valid result.",
].join(" ");

type CleanupFailureReporter = (failure: unknown) => void;

function reportCleanupFailureBestEffort(
  reportCleanupFailure: CleanupFailureReporter | undefined,
  failure: unknown,
): void {
  if (reportCleanupFailure === undefined) {
    return;
  }
  try {
    reportCleanupFailure(failure);
  } catch (reporterFailure) {
    // This observer has no recovery path, so its own failure is intentionally
    // suppressed and cannot replace the job/HTTP outcome already selected.
    void reporterFailure;
  }
}

async function disposeProvider(
  provider: TextGenerationProvider,
  reportCleanupFailure: CleanupFailureReporter | undefined,
): Promise<void> {
  try {
    await provider.dispose?.();
  } catch (failure) {
    reportCleanupFailureBestEffort(reportCleanupFailure, failure);
  }
}

/**
 * Evaluates immutable manuscript snapshots through the editorial_review
 * provider step (#316). The snapshot commits before the asynchronous
 * provider call; a provider failure propagates so the terminal-job bridge
 * records a failed job, and no findings are fabricated. The service never
 * passes a client-supplied model through to persistence and never edits
 * live content.
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

  /** Capture, assess through the provider, and persist one visible project. */
  async evaluateProject(
    principal: Principal,
    projectId: string,
    reportCleanupFailure?: CleanupFailureReporter,
  ): Promise<EditorialAssessment> {
    const scope = scopeForPrincipal(principal);
    const captured = this.store.captureReviewSnapshot(scope, projectId, { now: this.now() });
    const provider: TextProviderName = this.provenance.provider;
    const taskProvider = this.providerFactory(provider);
    try {
      const chapters = chapterWordCounts(captured.documents);
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
              thin_below: 250,
            }),
          ),
        },
      });
      const issues = coerceEditorialFindings(
        safeLoadJson(dumpJson(result.content)),
        captured.documents,
      );
      const recorded = this.store.recordSnapshotReview(scope, projectId, {
        snapshotId: captured.snapshotId,
        provider: result.provider,
        model: result.model,
        summary: EDITORIAL_SUMMARY,
        now: this.now(),
        issues,
      });
      return editorialAssessment(recorded);
    } finally {
      await disposeProvider(taskProvider, reportCleanupFailure);
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
