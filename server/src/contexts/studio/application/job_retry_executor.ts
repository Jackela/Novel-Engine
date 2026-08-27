import {
  isTextProviderName,
  type TextGenerationProvider,
  TextGenerationProviderError,
  type TextGenerationProviderFactory,
  type TextProviderName,
} from "../../../contexts/ai/application/ports/text_generation.js";
import type { Principal } from "../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import { NotFoundError } from "../domain/exceptions.js";
import type { SnapshotArtifactService } from "./export_artifact_service.js";
import { collectLoreEntries } from "./lorebook.js";
import {
  dumpJson,
  exportJobResultJson,
  jobPayload,
  reviewJobResultJson,
  safeLoadJson,
} from "./payloads.js";
import type { JobRecord, ProjectScope, StudioStore } from "./ports/studio_store.js";
import { scopeForPrincipal } from "./ports/studio_store.js";
import {
  INVALID_PROPOSAL_PROSE,
  OPERATION_STEPS,
  resolvedTokenCount,
  SYSTEM_PROMPT,
} from "./proposal_service.js";
import { buildProposalUserPrompt, collectResidentContextSource } from "./resident_context.js";
import type { ReviewService } from "./review_service.js";
import { isProposalMarkdownProse, sanitizeProposalMarkdown } from "./sanitization.js";

const RETRYABLE_STATUSES = new Set(["failed", "interrupted"]);

const ONLY_FAILED_RETRIED = "Only failed or interrupted jobs may be retried.";
const IMPORT_NOT_RETRIED = "Import jobs cannot be retried.";

export interface JobRetryExecutorOptions {
  readonly now?: (() => Date) | undefined;
  readonly providerFactory: TextGenerationProviderFactory;
}

/**
 * Executes the retry chain (#272): a failed or interrupted job is re-run as a
 * NEW job that starts `running` with a first event naming the original,
 * reaches a terminal state synchronously, and never mutates the original.
 * Import jobs are refused outright.
 */
export class JobRetryExecutor {
  private readonly store: StudioStore;
  private readonly reviews: ReviewService;
  private readonly artifacts: SnapshotArtifactService;
  private readonly providerFactory: TextGenerationProviderFactory;
  private readonly now: () => Date;

  constructor(
    store: StudioStore,
    reviews: ReviewService,
    artifacts: SnapshotArtifactService,
    options: JobRetryExecutorOptions,
  ) {
    this.store = store;
    this.reviews = reviews;
    this.artifacts = artifacts;
    this.providerFactory = options.providerFactory;
    this.now = options.now ?? (() => new Date());
  }

  async reexecuteProjectJob(
    principal: Principal,
    projectId: string,
    jobId: string,
    reportCleanupFailure: (failure: unknown) => void,
  ): Promise<Record<string, unknown>> {
    const scope = scopeForPrincipal(principal);
    const original = this.store.findJob(scope, projectId, jobId);
    if (!RETRYABLE_STATUSES.has(original.status)) {
      throw new InvalidOperationError(ONLY_FAILED_RETRIED);
    }
    if (original.kind === "import") {
      throw new InvalidOperationError(IMPORT_NOT_RETRIED);
    }
    const retry = this.store.addJob(scope, {
      projectId: original.projectId,
      documentId: original.documentId,
      kind: original.kind,
      operation: original.operation,
      status: "running",
      provider: original.provider,
      model: original.model,
      requestJson: original.requestJson,
      resultJson: dumpJson({}),
      error: null,
      retryOfJobId: original.id,
      eventDetailsJson: dumpJson({ retry_of: original.id }),
      now: this.now(),
    });
    try {
      if (retry.kind === "proposal") {
        return await this.reexecuteProposalJob(scope, retry, reportCleanupFailure);
      }
      if (retry.kind === "review") {
        return this.reexecuteReviewJob(principal, scope, retry);
      }
      if (retry.kind === "export") {
        return await this.reexecuteExportJob(principal, scope, retry);
      }
      throw new InvalidOperationError(`Unsupported job kind for retry: ${retry.kind}`);
    } catch (error) {
      if (
        !(error instanceof InvalidOperationError) &&
        !(error instanceof NotFoundError) &&
        !(error instanceof TextGenerationProviderError)
      ) {
        throw error;
      }
      return jobPayload(
        this.store.markJobOutcome(scope, projectId, retry.id, {
          status: "failed",
          error: error.message,
          eventDetailsJson: dumpJson({ error: error.message }),
          now: this.now(),
        }),
      );
    }
  }

  private async reexecuteProposalJob(
    scope: ProjectScope,
    retry: JobRecord,
    reportCleanupFailure: (failure: unknown) => void,
  ): Promise<Record<string, unknown>> {
    const request = safeLoadJson(retry.requestJson);
    const instruction = typeof request.instruction === "string" ? request.instruction : "";
    const baseRevisionId =
      typeof request.base_revision_id === "string" ? request.base_revision_id : null;
    const step = OPERATION_STEPS[retry.operation];
    if (retry.documentId === null || baseRevisionId === null || step === undefined) {
      throw new InvalidOperationError("Original AI job is missing its request context.");
    }
    if (!isTextProviderName(retry.provider)) {
      throw new InvalidOperationError(`Unsupported text generation provider: ${retry.provider}`);
    }
    const providerName: TextProviderName = retry.provider;
    const document = this.store.findDocument(scope, retry.projectId, retry.documentId);
    const revision = document.currentRevision;
    if (revision === null) {
      throw new InvalidOperationError("Document has no current revision.");
    }
    let provider: TextGenerationProvider | undefined;
    try {
      provider = this.providerFactory(providerName);
      const result = await provider.generateStructured({
        step,
        systemPrompt: SYSTEM_PROMPT,
        // A retried generation is a proposal generation too (#314): it assembles
        // the same resident context instead of the amnesiac historical shape.
        userPrompt: buildProposalUserPrompt({
          operation: retry.operation,
          instruction,
          source: collectResidentContextSource(this.store, scope, retry.projectId, document),
          manuscriptMarkdown: revision.contentMarkdown,
          loreEntries: collectLoreEntries(this.store, scope, retry.projectId),
        }),
        responseSchema: { chapter_markdown: { type: "string" } },
        metadata: {
          operation: retry.operation,
          document_id: document.id,
          base_revision_id: revision.id,
          chapter_number: document.position,
          title: document.title,
        },
      });
      const outcome = this.proposalOutcome(result);
      const now = this.now();
      this.store.addUsageEvent(scope, {
        projectId: retry.projectId,
        jobId: retry.id,
        provider: result.provider,
        model: result.model,
        promptTokens: resolvedTokenCount(result.promptTokens, instruction),
        completionTokens: resolvedTokenCount(result.completionTokens, outcome.proposal),
        requestEvidenceJson: dumpJson({
          operation: retry.operation,
          base_revision_id: revision.id,
        }),
        now,
      });
      return jobPayload(
        this.store.markJobOutcome(scope, retry.projectId, retry.id, {
          status: "completed",
          model: result.model,
          resultJson: dumpJson({
            proposal_markdown: outcome.proposal,
            base_revision_id: revision.id,
            accepted_revision_id: null,
          }),
          error: null,
          eventDetailsJson: dumpJson({ proposal_only: true }),
          now,
        }),
      );
    } finally {
      if (provider !== undefined) {
        try {
          await provider.dispose?.();
        } catch (cleanupFailure) {
          try {
            reportCleanupFailure(cleanupFailure);
          } catch {
            // The observer cannot replace the outcome already selected above.
          }
        }
      }
    }
  }

  private proposalOutcome(result: { content: { chapter_markdown?: unknown } }): {
    proposal: string;
  } {
    const chapterMarkdown = result.content.chapter_markdown;
    if (typeof chapterMarkdown !== "string") {
      throw new TextGenerationProviderError(INVALID_PROPOSAL_PROSE);
    }
    const proposal = sanitizeProposalMarkdown(chapterMarkdown);
    if (!isProposalMarkdownProse(proposal)) {
      throw new TextGenerationProviderError(INVALID_PROPOSAL_PROSE);
    }
    return { proposal };
  }

  private async reexecuteReviewJob(
    principal: Principal,
    scope: ProjectScope,
    retry: JobRecord,
  ): Promise<Record<string, unknown>> {
    const assessment = await this.reviews.evaluateProject(principal, retry.projectId);
    return jobPayload(
      this.store.markJobOutcome(scope, retry.projectId, retry.id, {
        status: "completed",
        resultJson: reviewJobResultJson(assessment),
        error: null,
        eventDetailsJson: dumpJson({ review_id: assessment.id }),
        now: this.now(),
      }),
    );
  }

  private async reexecuteExportJob(
    principal: Principal,
    scope: ProjectScope,
    retry: JobRecord,
  ): Promise<Record<string, unknown>> {
    const request = safeLoadJson(retry.requestJson);
    const format = request.format;
    if (format !== "markdown" && format !== "docx" && format !== "epub") {
      throw new InvalidOperationError("Original export job is missing its format.");
    }
    const artifact = await this.artifacts.materializeSnapshotArtifact(
      principal,
      retry.projectId,
      format,
    );
    return jobPayload(
      this.store.markJobOutcome(scope, retry.projectId, retry.id, {
        status: "completed",
        resultJson: exportJobResultJson(retry.projectId, artifact),
        error: null,
        eventDetailsJson: dumpJson({ export_id: artifact.id }),
        now: this.now(),
      }),
    );
  }
}
