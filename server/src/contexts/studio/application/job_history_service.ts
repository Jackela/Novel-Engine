import type { Principal } from "../../../shared/application/ports/auth.js";
import type { SnapshotArtifactService } from "./export_artifact_service.js";
import { JobRetryExecutor, type JobRetryExecutorOptions } from "./job_retry_executor.js";
import { dumpJson, exportJobResultJson, jobPayload, reviewJobResultJson } from "./payloads.js";
import type { ExportArtifactFormat } from "./ports/export_store.js";
import type { StudioStore } from "./ports/studio_store.js";
import { scopeForPrincipal } from "./ports/studio_store.js";
import type { ReviewService } from "./review_service.js";

/** Honest provenance for the deterministic studio renderers (no AI model). */
const STUDIO_EXPORTER_PROVIDER = "studio";

export interface JobHistoryServiceOptions {
  readonly now?: JobRetryExecutorOptions["now"];
  readonly providerFactory: JobRetryExecutorOptions["providerFactory"];
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
    });
    this.now = options.now ?? (() => new Date());
  }

  /** The audit listing: newest job first, each event stream newest first. */
  collectProjectJobs(principal: Principal, projectId: string): Array<Record<string, unknown>> {
    return this.store
      .collectProjectJobs(scopeForPrincipal(principal), projectId)
      .map((job) => jobPayload(job));
  }

  /** The terminal-Job bridge over a fresh editorial assessment. */
  recordReviewJob(principal: Principal, projectId: string): Record<string, unknown> {
    const scope = scopeForPrincipal(principal);
    const assessment = this.reviews.evaluateProject(principal, projectId);
    const job = this.store.addJob(scope, {
      projectId,
      documentId: null,
      kind: "review",
      operation: "review",
      status: "completed",
      provider: assessment.provider,
      model: assessment.model,
      requestJson: dumpJson({}),
      resultJson: reviewJobResultJson(assessment),
      error: null,
      eventDetailsJson: dumpJson({ review_id: assessment.id }),
      now: this.now(),
    });
    return jobPayload(job);
  }

  /** The terminal-Job bridge over a materialized export artifact (#271). */
  async recordExportJob(
    principal: Principal,
    projectId: string,
    format: ExportArtifactFormat,
  ): Promise<Record<string, unknown>> {
    const scope = scopeForPrincipal(principal);
    const artifact = await this.artifacts.materializeSnapshotArtifact(principal, projectId, format);
    const job = this.store.addJob(scope, {
      projectId,
      documentId: null,
      kind: "export",
      operation: "export",
      status: "completed",
      provider: STUDIO_EXPORTER_PROVIDER,
      model: "",
      requestJson: dumpJson({ format }),
      resultJson: exportJobResultJson(projectId, artifact),
      error: null,
      eventDetailsJson: dumpJson({ export_id: artifact.id }),
      now: this.now(),
    });
    return jobPayload(job);
  }

  /** Retry a failed/interrupted job; see JobRetryExecutor for the contract. */
  reexecuteProjectJob(
    principal: Principal,
    projectId: string,
    jobId: string,
    reportCleanupFailure: (failure: unknown) => void,
  ): Promise<Record<string, unknown>> {
    return this.retries.reexecuteProjectJob(principal, projectId, jobId, reportCleanupFailure);
  }
}
