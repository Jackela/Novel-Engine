import {
  type ProviderStep,
  TextGenerationCancelledError,
  type TextGenerationProvider,
  TextGenerationProviderError,
  type TextGenerationProviderFactory,
  type TextGenerationStreamOutcome,
  type TextGenerationTask,
  type TextProviderName,
} from "../../../contexts/ai/application/ports/text_generation.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import type { InFlightOperationGuard } from "./operation_in_flight.js";
import type { ProposalStreamFramePayload } from "./payload_schemas/proposal_frame.js";
import { jobPayload, safeLoadJson } from "./payloads.js";
import type { StudioJobLedgerStore } from "./ports/job_ledger_store.js";
import type { JobRecord } from "./ports/job_records.js";
import type { ProposalContextStore } from "./ports/proposal_context_store.js";
import {
  admitProposalOperation,
  admitTextProvider,
  buildProposalSeed,
  type ProposalGenerationRequest,
  type ProposalRetryRequest,
  type ProposalStreamOptions,
  proposalRevisionFromContext,
  proposalStepForOperation,
} from "./proposal_admission.js";
import {
  buildProposalTask,
  completedProposalJob,
  completedProposalLanding,
  createProposalCodePointCounter,
  failedProposalJob,
  includeProposalDelta,
  type ProposalJobSeed,
  validatedProposalOrThrow,
} from "./proposal_landing.js";
import { proposalRetryStaleBaseOutcome } from "./proposal_retry_base_outcome.js";
import { disposeProvider, type ProviderCleanupFailureReporter } from "./provider_disposal.js";

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
    // #305: the provider call runs before any job row exists, so identical
    // concurrent submissions are deduplicated by the in-flight guard — the
    // loser receives a 409 instead of running the work twice. Enter before
    // resolving the revision so a committed deletion still owns the project
    // throughout post-commit artifact cleanup rather than degrading to 404.
    const permit = this.inFlight.acquire({
      projectId: request.projectId,
      documentId: request.documentId,
      operation: request.operation,
    });
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
        if (!(error instanceof TextGenerationProviderError)) {
          throw error;
        }
        return failedProposalJob(
          this.jobs,
          request.scope,
          target.seed,
          target.revisionId,
          error.message,
        );
      }
    } finally {
      try {
        if (provider !== undefined) {
          await disposeProvider(provider, reportCleanupFailure);
        }
      } finally {
        permit.release();
      }
    }
  }

  /**
   * Streaming twin of `draft`: identical admission, in-flight guarding,
   * validation, and job/usage landing, but the proposal markdown is yielded
   * as deltas while the provider writes. The permit is handed to
   * `ownPermit` instead of being released here — the caller owns its
   * session-scoped release.
   */
  async *stream(
    request: ProposalGenerationRequest,
    options: ProposalStreamOptions,
  ): AsyncGenerator<ProposalStreamFramePayload, void, void> {
    const { step, providerName } = admitProposalOperation(request.operation, request.provider);
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
        const accumulated: string[] = [];
        const codePoints = createProposalCodePointCounter();
        let reported: TextGenerationStreamOutcome | undefined;
        for await (const delta of stream(target.task, {
          signal: options.signal,
          onOutcome: (value) => {
            reported = value;
          },
        })) {
          includeProposalDelta(codePoints, delta);
          accumulated.push(delta);
          yield { type: "delta", text: delta };
        }
        if (options.signal?.aborted === true) return;
        const { proposal } = validatedProposalOrThrow({
          content: { chapter_markdown: accumulated.join("") },
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
        if (error instanceof TextGenerationCancelledError) return;
        if (!(error instanceof TextGenerationProviderError)) {
          throw error;
        }
        failedProposalJob(this.jobs, request.scope, target.seed, target.revisionId, error.message);
        yield { type: "error", error: { code: "PROVIDER_FAILED", message: error.message } };
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
    const stored = safeLoadJson(retry.requestJson);
    const instruction = typeof stored.instruction === "string" ? stored.instruction : "";
    const baseRevisionId =
      typeof stored.base_revision_id === "string" ? stored.base_revision_id : null;
    if (retry.documentId === null || baseRevisionId === null) {
      throw new InvalidOperationError("Original AI job is missing its request context.");
    }
    // A stored operation without a provider step has lost its request context.
    const step = proposalStepForOperation(retry.operation);
    if (step === undefined) {
      throw new InvalidOperationError("Original AI job is missing its request context.");
    }
    const providerName = admitTextProvider(retry.provider);
    const context = this.proposalContext.readProposalContext(
      request.scope,
      retry.projectId,
      retry.documentId,
    );
    const { revision } = proposalRevisionFromContext(context);
    if (revision.id !== baseRevisionId) {
      return this.jobs.markJobOutcome(
        request.scope,
        retry.projectId,
        retry.id,
        proposalRetryStaleBaseOutcome(baseRevisionId, revision.id, request.now()),
      );
    }
    let provider: TextGenerationProvider | undefined;
    try {
      const task = buildProposalTask(
        step,
        retry.operation,
        instruction,
        context,
        this.loreBudgetCharacters,
      );
      provider = this.providerFactory(providerName);
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
            instruction,
          },
          { operation: retry.operation, revisionId: baseRevisionId, now: request.now() },
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
