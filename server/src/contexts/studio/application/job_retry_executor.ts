import {
  type TextGenerationProvider,
  TextGenerationProviderError,
  type TextGenerationProviderFactory,
} from "../../../contexts/ai/application/ports/text_generation.js";
import type { Principal } from "../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import {
  ExportArtifactWriteError,
  ExportSourceInvalidatedError,
  NotFoundError,
  ReviewSourceInvalidatedError,
} from "../domain/exceptions.js";
import { isExportArtifactFormat } from "./export_artifact_identity.js";
import type { SnapshotArtifactService } from "./export_artifact_service.js";
import { dumpJson, jobPayload, safeLoadJson } from "./payloads.js";
import type { JobRecord, ProjectScope, StudioStore } from "./ports/studio_store.js";
import { scopeForPrincipal } from "./ports/studio_store.js";
import {
  buildProposalTask,
  disposeProvider,
  resolvedTokenCount,
  validatedProposalOrThrow,
} from "./proposal_landing.js";
import {
  admitTextProvider,
  proposalStepForOperation,
  resolveProposalRevision,
} from "./proposal_pipeline.js";
import type { ReviewService } from "./review_service.js";

export interface JobRetryExecutorOptions {
  readonly now?: (() => Date) | undefined;
  readonly providerFactory: TextGenerationProviderFactory;
  /** Lorebook injection budget (#445); undefined keeps the adjudicated default. */
  readonly loreBudgetCharacters?: number | undefined;
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
  private readonly loreBudgetCharacters: number | undefined;
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
    this.loreBudgetCharacters = options.loreBudgetCharacters;
    this.now = options.now ?? (() => new Date());
  }

  async reexecuteProjectJob(
    principal: Principal,
    projectId: string,
    jobId: string,
    requestKey: string,
    reportCleanupFailure: (failure: unknown) => void,
  ): Promise<Record<string, unknown>> {
    const scope = scopeForPrincipal(principal);
    const replay = this.store.findJobRetry(scope, projectId, jobId, requestKey);
    if (replay !== null) {
      return this.claimAndExecute(
        principal,
        scope,
        projectId,
        jobId,
        requestKey,
        reportCleanupFailure,
      );
    }
    const source = this.store.findJob(scope, projectId, jobId);
    if (source.kind === "export") {
      return this.artifacts.withRendererPermit(projectId, () =>
        this.claimAndExecute(principal, scope, projectId, jobId, requestKey, reportCleanupFailure),
      );
    }
    return this.claimAndExecute(
      principal,
      scope,
      projectId,
      jobId,
      requestKey,
      reportCleanupFailure,
    );
  }

  private async claimAndExecute(
    principal: Principal,
    scope: ProjectScope,
    projectId: string,
    jobId: string,
    requestKey: string,
    reportCleanupFailure: (failure: unknown) => void,
  ): Promise<Record<string, unknown>> {
    const claim = this.store.claimJobRetry(scope, {
      projectId,
      sourceJobId: jobId,
      requestKey,
      now: this.now(),
    });
    if (!claim.created) return jobPayload(claim.job);
    const retry = claim.job;
    try {
      if (retry.kind === "proposal") {
        return await this.reexecuteProposalJob(scope, retry, reportCleanupFailure);
      }
      if (retry.kind === "review") {
        return await this.reexecuteReviewJob(principal, scope, retry, reportCleanupFailure);
      }
      if (retry.kind === "export") {
        return await this.reexecuteExportJob(principal, retry, reportCleanupFailure);
      }
      throw new InvalidOperationError(`Unsupported job kind for retry: ${retry.kind}`);
    } catch (error) {
      if (
        !(error instanceof InvalidOperationError) &&
        !(error instanceof NotFoundError) &&
        !(error instanceof ExportArtifactWriteError) &&
        !(error instanceof ExportSourceInvalidatedError) &&
        !(error instanceof ReviewSourceInvalidatedError) &&
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
    if (retry.documentId === null || baseRevisionId === null) {
      throw new InvalidOperationError("Original AI job is missing its request context.");
    }
    // A stored operation without a provider step has lost its request context.
    const step = proposalStepForOperation(retry.operation);
    if (step === undefined) {
      throw new InvalidOperationError("Original AI job is missing its request context.");
    }
    const providerName = admitTextProvider(retry.provider);
    const { document, revision } = resolveProposalRevision(
      this.store,
      scope,
      retry.projectId,
      retry.documentId,
    );
    let provider: TextGenerationProvider | undefined;
    try {
      provider = this.providerFactory(providerName);
      // A retried generation is a proposal generation too (#314): it assembles
      // the same resident context instead of the amnesiac historical shape.
      const result = await provider.generateStructured(
        buildProposalTask(
          step,
          retry.operation,
          instruction,
          this.store,
          scope,
          retry.projectId,
          document,
          revision,
          this.loreBudgetCharacters,
        ),
      );
      const outcome = validatedProposalOrThrow(result);
      const now = this.now();
      // #392: the outcome transition and its usage event commit together, so
      // a retried proposal never completes without its usage-ledger row.
      return jobPayload(
        this.store.markJobOutcomeWithUsage(scope, retry.projectId, retry.id, {
          outcome: {
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
          },
          usage: {
            provider: result.provider,
            model: result.model,
            promptTokens: resolvedTokenCount(result.promptTokens, instruction),
            completionTokens: resolvedTokenCount(result.completionTokens, outcome.proposal),
            requestEvidenceJson: dumpJson({
              operation: retry.operation,
              base_revision_id: revision.id,
            }),
          },
        }),
      );
    } finally {
      if (provider !== undefined) {
        await disposeProvider(provider, reportCleanupFailure);
      }
    }
  }

  private async reexecuteReviewJob(
    principal: Principal,
    scope: ProjectScope,
    retry: JobRecord,
    reportCleanupFailure: (failure: unknown) => void,
  ): Promise<Record<string, unknown>> {
    const evaluation = await this.reviews.evaluateProject(principal, retry.projectId, {
      provider: admitTextProvider(retry.provider),
      reportCleanupFailure,
    });
    try {
      return jobPayload(
        this.store.completeReviewRetryJob(scope, retry.projectId, retry.id, evaluation).job,
      );
    } catch (error) {
      if (!(error instanceof ReviewSourceInvalidatedError)) throw error;
      return jobPayload(
        this.store.markJobOutcome(scope, retry.projectId, retry.id, {
          status: "failed",
          model: evaluation.model,
          error: error.message,
          eventDetailsJson: dumpJson({ error: error.message }),
          now: this.now(),
        }),
      );
    }
  }

  private async reexecuteExportJob(
    principal: Principal,
    retry: JobRecord,
    reportCleanupFailure: (failure: unknown) => void,
  ): Promise<Record<string, unknown>> {
    const request = safeLoadJson(retry.requestJson);
    const format = request.format;
    if (!isExportArtifactFormat(format)) {
      throw new InvalidOperationError("Original export job is missing its format.");
    }
    const completed = await this.artifacts.completeExportRetryJob(
      principal,
      retry.projectId,
      retry.id,
      format,
      { reportCleanupFailure },
    );
    return jobPayload(completed.job);
  }
}
