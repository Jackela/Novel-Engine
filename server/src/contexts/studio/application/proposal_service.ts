import {
  type TextGenerationProvider,
  TextGenerationProviderError,
  type TextGenerationProviderFactory,
} from "../../../contexts/ai/application/ports/text_generation.js";
import type { Principal } from "../../../shared/application/ports/auth.js";
import type { InFlightOperationGuard } from "./operation_in_flight.js";
import { jobPayload } from "./payloads.js";
import {
  buildProposalTask,
  completedProposalJob,
  disposeProvider,
  failedProposalJob,
  type ProviderCleanupFailureReporter,
  validatedProposalOrThrow,
} from "./proposal_landing.js";
import {
  admitProposalOperation,
  buildProposalSeed,
  resolveProposalRevision,
} from "./proposal_pipeline.js";

export {
  INVALID_PROPOSAL_PROSE,
  OPERATION_STEPS,
  resolvedTokenCount,
  SYSTEM_PROMPT,
} from "./proposal_landing.js";

import type { StudioStore } from "./ports/studio_store.js";
import { scopeForPrincipal } from "./ports/studio_store.js";
import type { ProposalStreamSession } from "./proposal_streaming.js";
import { streamProposal } from "./proposal_streaming.js";

export interface ProposalDraftInput {
  readonly operation: string;
  readonly instruction: string;
  readonly provider: string;
}

/**
 * The AI proposal pipeline: proposals are persisted on jobs and never touch
 * the manuscript until the author accepts one. Manuscript text crosses the
 * provider boundary only inside the untrusted JSON block, and every proposal
 * is sanitized through the single table-driven source before it is returned
 * or persisted.
 */
export class AiProposalService {
  private readonly store: StudioStore;
  private readonly providerFactory: TextGenerationProviderFactory;
  private readonly inFlight: InFlightOperationGuard;
  private readonly now: () => Date;
  private readonly loreBudgetCharacters: number | undefined;

  constructor(
    store: StudioStore,
    providerFactory: TextGenerationProviderFactory,
    inFlight: InFlightOperationGuard,
    now: () => Date = () => new Date(),
    /** Lorebook injection budget (#445); undefined keeps the adjudicated default. */
    loreBudgetCharacters?: number | undefined,
  ) {
    this.store = store;
    this.providerFactory = providerFactory;
    this.inFlight = inFlight;
    this.now = now;
    this.loreBudgetCharacters = loreBudgetCharacters;
  }

  /** Generate a proposal for a document's current revision and record it on a job. */
  async draftProposal(
    principal: Principal,
    projectId: string,
    documentId: string,
    input: ProposalDraftInput,
    reportCleanupFailure: ProviderCleanupFailureReporter,
  ): Promise<Record<string, unknown>> {
    const scope = scopeForPrincipal(principal);
    const { step, providerName } = admitProposalOperation(input.operation, input.provider);
    const operation = input.operation;
    const instruction = input.instruction;
    // #305: the provider call runs before any job row exists, so identical
    // concurrent submissions are deduplicated by the in-flight guard — the
    // loser receives a 409 instead of running the work twice. Enter before
    // resolving the revision so a committed deletion still owns the project
    // throughout post-commit artifact cleanup rather than degrading to 404.
    const inFlightTarget = {
      projectId,
      documentId,
      operation,
    };
    const permit = this.inFlight.acquire(inFlightTarget);

    let provider: TextGenerationProvider | undefined;

    try {
      const { document, revision } = resolveProposalRevision(
        this.store,
        scope,
        projectId,
        documentId,
      );
      const seed = buildProposalSeed({
        projectId,
        documentId,
        operation,
        provider: providerName,
        instruction,
        baseRevisionId: revision.id,
        now: this.now(),
      });
      try {
        provider = this.providerFactory(providerName);
        const result = await provider.generateStructured(
          buildProposalTask(
            step,
            operation,
            instruction,
            this.store,
            scope,
            projectId,
            document,
            revision,
            this.loreBudgetCharacters,
          ),
        );
        const { proposal } = validatedProposalOrThrow(result);
        return jobPayload(
          completedProposalJob(this.store, scope, seed, revision.id, {
            proposal,
            provider: providerName,
            model: result.model,
            promptTokens: result.promptTokens,
            completionTokens: result.completionTokens,
            instruction,
          }),
        );
      } catch (error) {
        if (!(error instanceof TextGenerationProviderError)) {
          throw error;
        }
        return jobPayload(failedProposalJob(this.store, scope, seed, revision.id, error.message));
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
   * #308 streaming twin of `draftProposal`: identical validation, in-flight
   * guarding, and job/usage landing, but the proposal markdown is handed
   * over as deltas while the provider writes. Unconfigured providers and
   * invalid input throw before any stream starts; a client abort persists
   * nothing. See `proposal_streaming.ts` for the frame vocabulary.
   */
  draftProposalStream(
    principal: Principal,
    projectId: string,
    documentId: string,
    input: ProposalDraftInput,
    reportCleanupFailure: ProviderCleanupFailureReporter,
    signal?: AbortSignal,
  ): ProposalStreamSession {
    return streamProposal(
      {
        store: this.store,
        providerFactory: this.providerFactory,
        inFlight: this.inFlight,
        now: this.now,
        loreBudgetCharacters: this.loreBudgetCharacters,
      },
      {
        principal,
        projectId,
        documentId,
        input,
        reportCleanupFailure,
        signal,
      },
    );
  }

  /**
   * Accept a completed proposal: gated (completed status, non-empty
   * proposal), idempotent (an accepted job returns unchanged), and the
   * accepted revision carries source `ai-accepted` with `metadata.ai_job_id`.
   */
  adoptProposal(principal: Principal, projectId: string, jobId: string): Record<string, unknown> {
    return jobPayload(
      this.store.acceptCompletedProposal(
        scopeForPrincipal(principal),
        projectId,
        jobId,
        this.now(),
      ),
    );
  }
}
