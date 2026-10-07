import type {
  ProviderStep,
  TextGenerationProvider,
  TextGenerationProviderFactory,
  TextGenerationTask,
  TextProviderName,
} from "../../../contexts/ai/application/ports/text_generation.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import { type InFlightOperationGuard, withInFlightPermit } from "./operation_in_flight.js";
import type { ProposalStreamFramePayload } from "./payload_schemas/proposal_frame.js";
import { jobPayload } from "./payloads.js";
import type { StudioJobLedgerStore } from "./ports/job_ledger_store.js";
import type { JobRecord } from "./ports/job_records.js";
import type { ProposalContextStore } from "./ports/proposal_context_store.js";
import {
  admitProposalOperation,
  buildProposalSeed,
  type ProposalGenerationRequest,
  type ProposalRetryRequest,
  type ProposalStreamOptions,
  proposalRevisionFromContext,
  recoverProposalRetryContext,
  replayedProposalJob,
} from "./proposal_admission.js";
import {
  buildProposalTask,
  completedProposalJob,
  completedProposalLanding,
  failedProposalJob,
  type ProposalJobSeed,
  replayedProposalFrame,
  validatedProposalOrThrow,
} from "./proposal_landing.js";
import { accumulateStreamedDeltas } from "./proposal_stream_accumulation.js";
import { disposeProvider, type ProviderCleanupFailureReporter } from "./provider_disposal.js";
import {
  firstRunFailureDisposition,
  streamingFailureDisposition,
} from "./studio_failure_classification.js";

/**
 * The execution-sequence half of the proposal pipeline: the one owner of the
 * prompt/landing configuration and of the complete ProposalContext → landed
 * Job sequence (admission, in-flight guarding, provider task construction,
 * generation, prose validation, and the completed/failed landing choice with
 * resource cleanup). Constructed once by the composition root; the
 * synchronous draft (#305), the streaming twin (#308), and the retry (#272)
 * are thin adapters over `draft`/`stream`/`retry` that keep only their
 * transport and landing-target differences. The request/admission half lives
 * in `proposal_admission.ts`; the landing shapes live in `proposal_landing.ts`.
 */

/** The captured context resolved into everything a generation needs. */
interface ProposalTarget {
  readonly seed: ProposalJobSeed;
  readonly revisionId: string;
  readonly task: TextGenerationTask;
}

export class ProposalGenerationPipeline {
  constructor(
    private readonly proposalContext: ProposalContextStore,
    private readonly jobs: StudioJobLedgerStore,
    private readonly providerFactory: TextGenerationProviderFactory,
    private readonly inFlight: InFlightOperationGuard,
    private readonly now: () => Date = () => new Date(),
    /** Lorebook injection budget (#445); undefined keeps the adjudicated default. */
    private readonly loreBudgetCharacters: number | undefined = undefined,
  ) {}

  /** Synchronous draft: guard → capture → generate → validate → land → dispose. */
  async draft(
    request: ProposalGenerationRequest,
    reportCleanupFailure: ProviderCleanupFailureReporter,
  ): Promise<JobRecord> {
    const { step, providerName } = admitProposalOperation(request.operation, request.provider);
    // DR-027: a stored request key replays its landed job before any work runs.
    const replayed = replayedProposalJob(this.jobs, request);
    if (replayed !== undefined) return replayed;
    // #305: the provider call runs before any job row exists, so identical
    // concurrent submissions are deduplicated by the in-flight guard — the
    // loser receives a 409 instead of running the work twice. Enter before
    // resolving the revision so a committed deletion still owns the project
    // throughout post-commit artifact cleanup rather than degrading to 404.
    const inFlightTarget = {
      projectId: request.projectId,
      documentId: request.documentId,
      operation: request.operation,
    };
    return withInFlightPermit(this.inFlight, inFlightTarget, async () => {
      let provider: TextGenerationProvider | undefined;
      try {
        const target = this.resolveTarget(request, step, providerName);
        try {
          provider = this.providerFactory(providerName);
          const result = await provider.generateStructured(target.task);
          const { proposal } = validatedProposalOrThrow(result);
          return completedProposalJob(this.jobs, request.scope, target.seed, target.revisionId, {
            proposal,
            provider: providerName,
            model: result.model,
            promptTokens: result.promptTokens,
            completionTokens: result.completionTokens,
            instruction: request.instruction,
          });
        } catch (error) {
          const disposition = firstRunFailureDisposition(error, "proposal");
          if (disposition.kind === "propagate") throw error;
          return failedProposalJob(this.jobs, request.scope, target, disposition.failure.message);
        }
      } finally {
        if (provider !== undefined) {
          await disposeProvider(provider, reportCleanupFailure);
        }
      }
    });
  }

  /**
   * Streaming twin of `draft`: identical admission, in-flight guarding,
   * validation, and job/usage landing, but the proposal markdown is yielded
   * as deltas while the provider writes. The permit is handed to
   * `ownPermit` instead of being released here — the caller owns its
   * session-scoped release, so the synchronous `withInFlightPermit` template
   * deliberately does not apply and must not release it when frames end.
   */
  async *stream(
    request: ProposalGenerationRequest,
    options: ProposalStreamOptions,
  ): AsyncGenerator<ProposalStreamFramePayload, void, void> {
    const { step, providerName } = admitProposalOperation(request.operation, request.provider);
    // DR-027: the stored key's terminal outcome is replayed as its own frame.
    const replayed = replayedProposalJob(this.jobs, request);
    if (replayed !== undefined) {
      yield replayedProposalFrame(replayed);
      return;
    }
    // #305 parity: identical concurrent submissions are deduplicated by the
    // in-flight guard — the loser receives a 409 instead of running work twice.
    // The guard precedes row resolution so post-commit deletion cleanup keeps
    // returning the project-exclusive conflict until it actually releases.
    options.ownPermit(
      this.inFlight.acquire({
        projectId: request.projectId,
        documentId: request.documentId,
        operation: request.operation,
      }),
    );
    let provider: TextGenerationProvider | undefined;
    const accumulated: string[] = [];
    try {
      const target = this.resolveTarget(request, step, providerName);
      try {
        provider = this.providerFactory(providerName);
        const stream = provider.generateStructuredStreaming?.bind(provider);
        if (stream === undefined) {
          throw new InvalidOperationError(
            `Provider '${providerName}' does not support streaming generation.`,
          );
        }
        const { reported } = yield* accumulateStreamedDeltas(
          stream,
          target.task,
          options.signal,
          accumulated,
        );
        // Drain the sink: a completed stream keeps no partial, so only text from
        // a stream that actually broke mid-flight survives for the failed job.
        const streamedMarkdown = accumulated.splice(0).join("");
        if (options.signal?.aborted === true) return;
        const { proposal } = validatedProposalOrThrow({
          content: { chapter_markdown: streamedMarkdown },
        });
        yield {
          type: "done",
          job: jobPayload(
            completedProposalJob(this.jobs, request.scope, target.seed, target.revisionId, {
              proposal,
              provider: providerName,
              model: reported?.model ?? "",
              promptTokens: reported?.promptTokens ?? null,
              completionTokens: reported?.completionTokens ?? null,
              instruction: request.instruction,
            }),
          ),
        };
      } catch (error) {
        const disposition = streamingFailureDisposition(error);
        // DR-022: an unconfigured provider never starts a stream and never
        // lands a failed job — the HTTP surface answers with the dedicated
        // PROVIDER_NOT_CONFIGURED envelope naming the missing credential;
        // unknown failures take the same propagate exit.
        if (disposition.kind === "propagate") throw error;
        if (disposition.kind === "abort") return;
        // DR-006: a stream that broke mid-flight persists its accumulated text
        // (sanitized) as `partial_markdown`; a completed stream drained the sink
        // above and persists none.
        const failure = disposition.failure.message;
        failedProposalJob(this.jobs, request.scope, target, failure, accumulated.join(""));
        yield { type: "error", error: { code: "PROVIDER_FAILED", message: failure } };
      }
    } finally {
      if (provider !== undefined) {
        await disposeProvider(provider, options.reportCleanupFailure);
      }
    }
  }

  /**
   * Retry of a claimed proposal job: no separate in-flight permit (the retry
   * surface holds one), and the landing transitions the reserved retry row
   * instead of inserting a fresh job. A stale immutable base lands the exact
   * stale-base failure; a missing stored request context refuses the retry.
   */
  async retry(request: ProposalRetryRequest): Promise<JobRecord> {
    const retry = request.retry;
    const recovery = recoverProposalRetryContext(request, this.proposalContext);
    if (recovery.kind === "stale-base") {
      return this.jobs.markJobOutcome(request.scope, retry.projectId, retry.id, recovery.outcome);
    }
    let provider: TextGenerationProvider | undefined;
    try {
      const task = buildProposalTask(
        recovery.step,
        retry.operation,
        recovery.instruction,
        recovery.context,
        this.loreBudgetCharacters,
      );
      provider = this.providerFactory(recovery.providerName);
      // A retried generation is a proposal generation too (#314): it assembles
      // the same resident context instead of the amnesiac historical shape.
      const result = await provider.generateStructured(task);
      const outcome = validatedProposalOrThrow(result);
      // #392: the outcome transition and its usage event commit together, in
      // the same landing shape a fresh draft lands by construction.
      return this.jobs.markJobOutcomeWithUsage(
        request.scope,
        retry.projectId,
        retry.id,
        completedProposalLanding(
          {
            proposal: outcome.proposal,
            provider: result.provider,
            model: result.model,
            promptTokens: result.promptTokens,
            completionTokens: result.completionTokens,
            instruction: recovery.instruction,
          },
          { operation: retry.operation, revisionId: recovery.baseRevisionId, now: request.now() },
        ),
      );
    } finally {
      if (provider !== undefined) {
        await disposeProvider(provider, request.reportCleanupFailure);
      }
    }
  }

  /** Reads one captured context and resolves its landing seed and task. */
  private resolveTarget(
    request: ProposalGenerationRequest,
    step: ProviderStep,
    providerName: TextProviderName,
  ): ProposalTarget {
    const context = this.proposalContext.readProposalContext(
      request.scope,
      request.projectId,
      request.documentId,
    );
    const { revision } = proposalRevisionFromContext(context);
    return {
      seed: buildProposalSeed({
        projectId: context.projectId,
        documentId: context.target.id,
        operation: request.operation,
        provider: providerName,
        instruction: request.instruction,
        baseRevisionId: revision.id,
        now: this.now(),
        requestKey: request.requestKey,
      }),
      revisionId: revision.id,
      task: buildProposalTask(
        step,
        request.operation,
        request.instruction,
        context,
        this.loreBudgetCharacters,
      ),
    };
  }
}
