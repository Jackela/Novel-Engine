import { TextGenerationProviderError } from "../../../contexts/ai/application/ports/text_generation.js";
import type { Principal } from "../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import {
  ExportArtifactWriteError,
  ExportCapacityExceededError,
  ExportSourceInvalidatedError,
  GenerationCapacityExceededError,
  NotFoundError,
  ReviewSourceInvalidatedError,
} from "../domain/exceptions.js";
import { isExportArtifactFormat } from "./export_artifact_identity.js";
import type { SnapshotArtifactService } from "./export_artifact_service.js";
import {
  exportRetryCapacityOutcome,
  replayedExportCapacityError,
} from "./export_retry_capacity_outcome.js";
import {
  generationRetryCapacityOutcome,
  replayedGenerationCapacityError,
} from "./generation_retry_capacity_outcome.js";
import { dumpJson, jobPayload, safeLoadJson } from "./payloads.js";
import type { StudioJobLedgerStore } from "./ports/job_ledger_store.js";
import type { JobRecord } from "./ports/job_records.js";
import type { ReviewOutcomeStore } from "./ports/review_outcome_store.js";
import type { ProjectScope } from "./ports/studio_store.js";
import { scopeForPrincipal } from "./ports/studio_store.js";
import { admitTextProvider } from "./proposal_admission.js";
import type { ProposalGenerationPipeline } from "./proposal_pipeline.js";
import type { ReviewService } from "./review_service.js";

export interface JobRetryExecutorOptions {
  readonly now?: (() => Date) | undefined;
  /** Owns the proposal generation sequence and its prompt/landing configuration. */
  readonly proposals: ProposalGenerationPipeline;
}

/**
 * Executes the retry chain (#272): a failed or interrupted job is re-run as a
 * NEW job that starts `running`, reaches a terminal state synchronously, and
 * never mutates the original. Import jobs are refused outright.
 */
export class JobRetryExecutor {
  private readonly proposals: ProposalGenerationPipeline;
  private readonly now: () => Date;

  constructor(
    private readonly jobs: StudioJobLedgerStore,
    private readonly reviewOutcomes: ReviewOutcomeStore,
    private readonly reviews: ReviewService,
    private readonly artifacts: SnapshotArtifactService,
    options: JobRetryExecutorOptions,
  ) {
    this.proposals = options.proposals;
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
    const replay = this.jobs.findJobRetry(scope, projectId, jobId, requestKey);
    if (replay !== null) {
      const capacityError =
        replayedExportCapacityError(replay) ?? replayedGenerationCapacityError(replay);
      if (capacityError !== null) throw capacityError;
      return this.claimAndExecute(
        principal,
        scope,
        projectId,
        jobId,
        requestKey,
        reportCleanupFailure,
      );
    }
    const source = this.jobs.findJob(scope, projectId, jobId);
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
    const claim = this.jobs.claimJobRetry(scope, {
      projectId,
      sourceJobId: jobId,
      requestKey,
      now: this.now(),
    });
    if (!claim.created) {
      const capacityError =
        replayedExportCapacityError(claim.job) ?? replayedGenerationCapacityError(claim.job);
      if (capacityError !== null) throw capacityError;
      return jobPayload(claim.job);
    }
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
        error instanceof ExportCapacityExceededError ||
        error instanceof GenerationCapacityExceededError
      ) {
        const outcome =
          error instanceof ExportCapacityExceededError
            ? exportRetryCapacityOutcome(retry, error, this.now())
            : generationRetryCapacityOutcome(retry, error, this.now());
        this.jobs.markJobOutcome(scope, projectId, retry.id, outcome);
        throw error;
      }
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
        this.jobs.markJobOutcome(scope, projectId, retry.id, {
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
    // The full retry sequence — stored-request decoding, admission, the
    // stale-base judgment, generation, and the landing on this reserved row —
    // lives in the pipeline, shared with the synchronous draft and the stream.
    return jobPayload(
      await this.proposals.retry({ scope, retry, reportCleanupFailure, now: this.now }),
    );
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
        this.reviewOutcomes.completeReviewRetryJob(scope, retry.projectId, retry.id, evaluation)
          .job,
      );
    } catch (error) {
      if (!(error instanceof ReviewSourceInvalidatedError)) throw error;
      return jobPayload(
        this.jobs.markJobOutcome(scope, retry.projectId, retry.id, {
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
