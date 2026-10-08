import type { TextGenerationExecutionOptions } from "../../../contexts/ai/application/ports/text_generation.js";
import type { Principal } from "../../../shared/application/ports/auth.js";
import { NotFoundError, OperationInFlightError } from "../domain/exceptions.js";
import type { SnapshotArtifactService } from "./export_artifact_service.js";
import { failedJobInput } from "./failed_job_input.js";
import { replayedJobPayload } from "./job_replay_payload.js";
import { JobRetryExecutor } from "./job_retry_executor.js";
import type { LoreExtractService } from "./lore_extract_service.js";
import { type InFlightOperationGuard, withInFlightPermit } from "./operation_in_flight.js";
import type { JobPayload, JobSummaryPayload } from "./payload_schemas/job.js";
import { dumpJson, jobPayload, jobSummaryPayload } from "./payloads.js";
import type { ExportArtifactFormat } from "./ports/export_store.js";
import type { StudioJobLedgerStore } from "./ports/job_ledger_store.js";
import type { JobPageCursor, JobPageInput } from "./ports/job_records.js";
import type { ProjectUsageAggregate } from "./ports/project_usage.js";
import type { EvaluatedReview, ReviewOutcomeStore } from "./ports/review_outcome_store.js";
import type { ProjectScope } from "./ports/studio_store.js";
import { scopeForPrincipal } from "./ports/studio_store.js";
import type { ProposalGenerationPipeline } from "./proposal_pipeline.js";
import type { ReviewService } from "./review_service.js";
import { firstRunFailureDisposition } from "./studio_failure_classification.js";

/** Honest provenance for the deterministic studio renderers (no AI model). */
const STUDIO_EXPORTER_PROVIDER = "studio";

interface JobHistoryServiceOptions {
  readonly now?: (() => Date) | undefined;
  /** Serializes identical exports and retries (#305); shared with proposals. */
  readonly inFlight: InFlightOperationGuard;
  /** Owns the proposal generation sequence shared with the proposal surface. */
  readonly proposals: ProposalGenerationPipeline;
  /** Owns the lorebook wizard's extraction sequence shared with its surface. */
  readonly loreExtractions: LoreExtractService;
}

interface JobHistoryPage {
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
  private readonly jobs: StudioJobLedgerStore;
  private readonly reviewOutcomes: ReviewOutcomeStore;
  private readonly reviews: ReviewService;
  private readonly artifacts: SnapshotArtifactService;
  private readonly retries: JobRetryExecutor;
  private readonly inFlight: InFlightOperationGuard;
  private readonly now: () => Date;

  constructor(
    jobs: StudioJobLedgerStore,
    reviewOutcomes: ReviewOutcomeStore,
    reviews: ReviewService,
    artifacts: SnapshotArtifactService,
    options: JobHistoryServiceOptions,
  ) {
    this.jobs = jobs;
    this.reviewOutcomes = reviewOutcomes;
    this.reviews = reviews;
    this.artifacts = artifacts;
    this.retries = new JobRetryExecutor(jobs, reviewOutcomes, reviews, artifacts, {
      now: options.now,
      proposals: options.proposals,
      loreExtractions: options.loreExtractions,
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
    const page = this.jobs.collectProjectJobSummaries(
      scopeForPrincipal(principal),
      projectId,
      input,
    );
    return { jobs: page.jobs.map((job) => jobSummaryPayload(job)), nextCursor: page.nextCursor };
  }

  /** One complete scoped Job; all known misses share the stable Job identity. */
  findProjectJob(principal: Principal, projectId: string, jobId: string): JobPayload {
    try {
      return jobPayload(this.jobs.findJob(scopeForPrincipal(principal), projectId, jobId));
    } catch (error) {
      if (!(error instanceof NotFoundError)) throw error;
      throw new NotFoundError(`Job not found: ${jobId}.`);
    }
  }

  /** The usage-ledger aggregation for the project surface (#317, #384). */
  aggregateProjectUsage(principal: Principal, projectId: string): ProjectUsageAggregate {
    return this.jobs.aggregateProjectUsage(scopeForPrincipal(principal), projectId, this.now());
  }

  /** The terminal-Job bridge over a fresh editorial assessment. */
  async recordReviewJob(
    principal: Principal,
    projectId: string,
    reportCleanupFailure?: (failure: unknown) => void,
    execution?: TextGenerationExecutionOptions,
  ): Promise<Record<string, unknown>> {
    const scope = scopeForPrincipal(principal);
    // #392: like proposal/export/retry, a review runs real provider work
    // before its terminal row exists, so identical concurrent reviews are
    // serialized by the in-flight guard instead of racing the provider.
    return withInFlightPermit(
      this.inFlight,
      { projectId, documentId: null, operation: "review" },
      () => this.recordReviewJobInner(principal, scope, projectId, reportCleanupFailure, execution),
    );
  }

  private async recordReviewJobInner(
    principal: Principal,
    scope: ProjectScope,
    projectId: string,
    reportCleanupFailure?: (failure: unknown) => void,
    execution?: TextGenerationExecutionOptions,
  ): Promise<Record<string, unknown>> {
    // DR-024: the review runs on the project's own provider, so its job row
    // must name that provider even when the attempt fails before an evaluation
    // exists — the retry chain re-admits the row's provider.
    const projectProvider = this.reviews.providerNameForProject(principal, projectId);
    let evaluation: EvaluatedReview | undefined;
    try {
      evaluation = await this.reviews.evaluateProject(principal, projectId, {
        reportCleanupFailure,
        execution,
      });
      const completed = this.reviewOutcomes.recordCompletedReviewJob(scope, evaluation);
      return jobPayload(completed.job);
    } catch (error) {
      const disposition = firstRunFailureDisposition(error, "review");
      if (disposition.kind === "propagate") throw error;
      return jobPayload(
        this.jobs.addJob(
          scope,
          failedJobInput({
            projectId,
            documentId: null,
            kind: "review",
            operation: "review",
            provider: evaluation?.provider ?? projectProvider,
            model: evaluation?.model ?? "",
            requestJson: dumpJson({}),
            resultJson: dumpJson({
              review_id: null,
              snapshot_id: null,
              summary: "",
              issues: [],
              ...(projectProvider === "acp" && execution?.agentExecution !== undefined
                ? { agent_execution: execution.agentExecution }
                : {}),
            }),
            error: disposition.failure.message,
            now: this.now(),
          }),
        ),
      );
    } finally {
      evaluation?.sourceLease?.release();
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
    return withInFlightPermit(
      this.inFlight,
      { projectId, documentId: null, operation: `export (${format})` },
      async () => {
        try {
          const completed = await this.artifacts.recordCompletedExportJob(
            principal,
            projectId,
            format,
            { reportCleanupFailure },
          );
          return jobPayload(completed.job);
        } catch (error) {
          const disposition = firstRunFailureDisposition(error, "export");
          if (disposition.kind === "propagate") throw error;
          return jobPayload(
            this.jobs.addJob(
              scope,
              failedJobInput({
                projectId,
                documentId: null,
                kind: "export",
                operation: "export",
                provider: STUDIO_EXPORTER_PROVIDER,
                model: "",
                requestJson: dumpJson({ format }),
                resultJson: dumpJson({
                  export_id: null,
                  snapshot_id: null,
                  format,
                  download_url: null,
                }),
                error: disposition.failure.message,
                now: this.now(),
              }),
            ),
          );
        }
      },
    );
  }

  /** Retry a failed/interrupted job; see JobRetryExecutor for the contract. */
  async reexecuteProjectJob(
    principal: Principal,
    projectId: string,
    jobId: string,
    requestKey: string,
    reportCleanupFailure: (failure: unknown) => void,
    execution?: TextGenerationExecutionOptions,
  ): Promise<Record<string, unknown>> {
    // Project deletion removes persistence before artifact cleanup completes;
    // preserve its exclusive 409 boundary before any durable replay lookup.
    this.inFlight.assertProjectNotExclusive(projectId);
    const replay = this.jobs.findJobRetry(
      scopeForPrincipal(principal),
      projectId,
      jobId,
      requestKey,
    );
    if (replay !== null) {
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
      return replayedJobPayload(replay);
    }
    // #305: a retry runs real work after its running row is created, so a
    // double-fired retry of the same job is deduplicated like the pipelines.
    return withInFlightPermit(
      this.inFlight,
      { projectId, documentId: null, operation: `retry (${jobId})` },
      () =>
        this.retries.reexecuteProjectJob(
          principal,
          projectId,
          jobId,
          requestKey,
          reportCleanupFailure,
          execution,
        ),
    );
  }
}
