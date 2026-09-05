import { TextGenerationProviderError } from "../../../contexts/ai/application/ports/text_generation.js";
import type { Principal } from "../../../shared/application/ports/auth.js";
import {
  ExportArtifactWriteError,
  ExportSourceInvalidatedError,
  NotFoundError,
  OperationInFlightError,
  ReviewSourceInvalidatedError,
} from "../domain/exceptions.js";
import type { SnapshotArtifactService } from "./export_artifact_service.js";
import { replayedExportCapacityError } from "./export_retry_capacity_outcome.js";
import { replayedGenerationCapacityError } from "./generation_retry_capacity_outcome.js";
import { JobRetryExecutor, type JobRetryExecutorOptions } from "./job_retry_executor.js";
import type { InFlightOperationGuard } from "./operation_in_flight.js";
import type { JobPayload, JobSummaryPayload } from "./payload_schemas/job.js";
import { dumpJson, jobPayload, jobSummaryPayload } from "./payloads.js";
import type { ExportArtifactFormat } from "./ports/export_store.js";
import type { JobPageCursor, JobPageInput } from "./ports/job_records.js";
import type {
  EvaluatedReview,
  ProjectScope,
  ProjectUsageAggregate,
  StudioStore,
} from "./ports/studio_store.js";
import { scopeForPrincipal } from "./ports/studio_store.js";
import type { ReviewService } from "./review_service.js";

/** Honest provenance for the deterministic studio renderers (no AI model). */
const STUDIO_EXPORTER_PROVIDER = "studio";

export interface JobHistoryServiceOptions {
  readonly now?: JobRetryExecutorOptions["now"];
  readonly providerFactory: JobRetryExecutorOptions["providerFactory"];
  /** Serializes identical exports and retries (#305); shared with proposals. */
  readonly inFlight: InFlightOperationGuard;
  /** Lorebook injection budget (#445); undefined keeps the adjudicated default. */
  readonly loreBudgetCharacters?: JobRetryExecutorOptions["loreBudgetCharacters"];
}

export interface JobHistoryPage {
  readonly jobs: JobSummaryPayload[];
  readonly nextCursor: JobPageCursor | null;
}

/**
 * The synchronous jobs model's shared surface (#272): the persisted audit
 * listing, the terminal-Job bridges that let review and export requests
 * report the spec's terminal job payload exactly like proposals have since
 * #268, and delegation of the retry chain to its executor.
 */
export class JobHistoryService {
  private readonly store: StudioStore;
  private readonly reviews: ReviewService;
  private readonly artifacts: SnapshotArtifactService;
  private readonly retries: JobRetryExecutor;
  private readonly inFlight: InFlightOperationGuard;
  private readonly now: () => Date;

  constructor(
    store: StudioStore,
    reviews: ReviewService,
    artifacts: SnapshotArtifactService,
    options: JobHistoryServiceOptions,
  ) {
    this.store = store;
    this.reviews = reviews;
    this.artifacts = artifacts;
    this.retries = new JobRetryExecutor(store, reviews, artifacts, {
      now: options.now,
      providerFactory: options.providerFactory,
      loreBudgetCharacters: options.loreBudgetCharacters,
    });
    this.inFlight = options.inFlight;
    this.now = options.now ?? (() => new Date());
  }

  /** The lightweight audit listing: newest summary first, with no nested bodies. */
  collectProjectJobSummaries(
    principal: Principal,
    projectId: string,
    input: JobPageInput,
  ): JobHistoryPage {
    const page = this.store.collectProjectJobSummaries(
      scopeForPrincipal(principal),
      projectId,
      input,
    );
    return { jobs: page.jobs.map((job) => jobSummaryPayload(job)), nextCursor: page.nextCursor };
  }

  /** One complete scoped Job; all known misses share the stable Job identity. */
  findProjectJob(principal: Principal, projectId: string, jobId: string): JobPayload {
    try {
      return jobPayload(this.store.findJob(scopeForPrincipal(principal), projectId, jobId));
    } catch (error) {
      if (!(error instanceof NotFoundError)) throw error;
      throw new NotFoundError("Job not found.");
    }
  }

  /** The usage-ledger aggregation for the project surface (#317, #384). */
  aggregateProjectUsage(principal: Principal, projectId: string): ProjectUsageAggregate {
    return this.store.aggregateProjectUsage(scopeForPrincipal(principal), projectId, this.now());
  }

  /** The terminal-Job bridge over a fresh editorial assessment. */
  async recordReviewJob(
    principal: Principal,
    projectId: string,
    reportCleanupFailure?: (failure: unknown) => void,
  ): Promise<Record<string, unknown>> {
    const scope = scopeForPrincipal(principal);
    // #392: like proposal/export/retry, a review runs real provider work
    // before its terminal row exists, so identical concurrent reviews are
    // serialized by the in-flight guard instead of racing the provider.
    const inFlightTarget = {
      projectId,
      documentId: null,
      operation: "review",
    };
    const permit = this.inFlight.acquire(inFlightTarget);
    try {
      return await this.recordReviewJobInner(principal, scope, projectId, reportCleanupFailure);
    } finally {
      permit.release();
    }
  }

  private async recordReviewJobInner(
    principal: Principal,
    scope: ProjectScope,
    projectId: string,
    reportCleanupFailure?: (failure: unknown) => void,
  ): Promise<Record<string, unknown>> {
    let evaluation: EvaluatedReview | undefined;
    try {
      evaluation = await this.reviews.evaluateProject(principal, projectId, {
        reportCleanupFailure,
      });
      const completed = this.store.recordCompletedReviewJob(scope, evaluation);
      return jobPayload(completed.job);
    } catch (error) {
      if (
        !(error instanceof TextGenerationProviderError) &&
        !(error instanceof ReviewSourceInvalidatedError)
      ) {
        throw error;
      }
      return jobPayload(
        this.store.addJob(scope, {
          projectId,
          documentId: null,
          kind: "review",
          operation: "review",
          status: "failed",
          provider: evaluation?.provider ?? this.reviews.providerName,
          model: evaluation?.model ?? "",
          requestJson: dumpJson({}),
          resultJson: dumpJson({ review_id: null, snapshot_id: null, summary: "", issues: [] }),
          error: error.message,
          eventDetailsJson: dumpJson({ error: error.message }),
          now: this.now(),
        }),
      );
    }
  }

  /** The terminal-Job bridge over a materialized export artifact (#271). */
  async recordExportJob(
    principal: Principal,
    projectId: string,
    format: ExportArtifactFormat,
    reportCleanupFailure?: (failure: unknown) => void,
  ): Promise<Record<string, unknown>> {
    const scope = scopeForPrincipal(principal);
    // #305: the artifact write runs before the terminal job row exists;
    // identical concurrent exports deduplicate through the in-flight guard
    // (different formats of one project may still run in parallel).
    const inFlightTarget = {
      projectId,
      documentId: null,
      operation: `export (${format})`,
    };
    const permit = this.inFlight.acquire(inFlightTarget);
    try {
      try {
        const completed = await this.artifacts.recordCompletedExportJob(
          principal,
          projectId,
          format,
          { reportCleanupFailure },
        );
        return jobPayload(completed.job);
      } catch (error) {
        if (
          !(error instanceof ExportArtifactWriteError) &&
          !(error instanceof ExportSourceInvalidatedError)
        ) {
          throw error;
        }
        return jobPayload(
          this.store.addJob(scope, {
            projectId,
            documentId: null,
            kind: "export",
            operation: "export",
            status: "failed",
            provider: STUDIO_EXPORTER_PROVIDER,
            model: "",
            requestJson: dumpJson({ format }),
            resultJson: dumpJson({
              export_id: null,
              snapshot_id: null,
              format,
              download_url: null,
            }),
            error: error.message,
            eventDetailsJson: dumpJson({ error: error.message }),
            now: this.now(),
          }),
        );
      }
    } finally {
      permit.release();
    }
  }

  /** Retry a failed/interrupted job; see JobRetryExecutor for the contract. */
  async reexecuteProjectJob(
    principal: Principal,
    projectId: string,
    jobId: string,
    requestKey: string,
    reportCleanupFailure: (failure: unknown) => void,
  ): Promise<Record<string, unknown>> {
    // Project deletion removes persistence before artifact cleanup completes;
    // preserve its exclusive 409 boundary before any durable replay lookup.
    this.inFlight.assertProjectNotExclusive(projectId);
    const replay = this.store.findJobRetry(
      scopeForPrincipal(principal),
      projectId,
      jobId,
      requestKey,
    );
    if (replay !== null) {
      const capacityError =
        replayedExportCapacityError(replay) ?? replayedGenerationCapacityError(replay);
      if (capacityError !== null) throw capacityError;
      if (replay.status === "running") {
        throw new OperationInFlightError(projectId, null, `retry (${jobId})`, 1);
      }
      if (
        replay.status !== "completed" &&
        replay.status !== "failed" &&
        replay.status !== "interrupted"
      ) {
        throw new Error(`Persisted retry Job has invalid status: ${replay.status}.`);
      }
      return jobPayload(replay);
    }
    // #305: a retry runs real work after its running row is created, so a
    // double-fired retry of the same job is deduplicated like the pipelines.
    const inFlightTarget = {
      projectId,
      documentId: null,
      operation: `retry (${jobId})`,
    };
    const permit = this.inFlight.acquire(inFlightTarget);
    try {
      return await this.retries.reexecuteProjectJob(
        principal,
        projectId,
        jobId,
        requestKey,
        reportCleanupFailure,
      );
    } finally {
      permit.release();
    }
  }
}
