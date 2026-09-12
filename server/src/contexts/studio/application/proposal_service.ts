import type { Principal } from "../../../shared/application/ports/auth.js";
import { jobPayload } from "./payloads.js";
import type { ProposalAcceptanceStore } from "./ports/proposal_acceptance_store.js";
import { scopeForPrincipal } from "./ports/studio_store.js";
import type { ProposalGenerationRequest } from "./proposal_admission.js";
import type { ProviderCleanupFailureReporter } from "./proposal_landing.js";
import type { ProposalGenerationPipeline } from "./proposal_pipeline.js";
import type { ProposalStreamSession } from "./proposal_streaming.js";
import { streamProposal } from "./proposal_streaming.js";

/**
 * Author-authored generation request: the operation step, a freeform
 * instruction, and the named provider. The model stays server-owned and
 * never travels with the request.
 */
export interface ProposalDraftInput {
  readonly operation: string;
  readonly instruction: string;
  readonly provider: string;
}

/**
 * The AI proposal surface: proposals are persisted on jobs and never touch
 * the manuscript until the author accepts one. The generation execution
 * sequence lives in `ProposalGenerationPipeline`; this service is the thin
 * adapter that decodes the request scope and wraps the landed job as the
 * HTTP payload.
 */
export class AiProposalService {
  private readonly proposalAcceptance: ProposalAcceptanceStore;
  private readonly pipeline: ProposalGenerationPipeline;
  private readonly now: () => Date;

  constructor(
    proposalAcceptance: ProposalAcceptanceStore,
    pipeline: ProposalGenerationPipeline,
    now: () => Date = () => new Date(),
  ) {
    this.proposalAcceptance = proposalAcceptance;
    this.pipeline = pipeline;
    this.now = now;
  }

  private generationRequest(
    principal: Principal,
    projectId: string,
    documentId: string,
    input: ProposalDraftInput,
  ): ProposalGenerationRequest {
    return {
      scope: scopeForPrincipal(principal),
      projectId,
      documentId,
      operation: input.operation,
      instruction: input.instruction,
      provider: input.provider,
    };
  }

  /** Generate a proposal for a document's current revision and record it on a job. */
  async draftProposal(
    principal: Principal,
    projectId: string,
    documentId: string,
    input: ProposalDraftInput,
    reportCleanupFailure: ProviderCleanupFailureReporter,
  ): Promise<Record<string, unknown>> {
    return jobPayload(
      await this.pipeline.draft(
        this.generationRequest(principal, projectId, documentId, input),
        reportCleanupFailure,
      ),
    );
  }

  /**
   * #308 streaming twin of `draftProposal`: identical execution sequence, but
   * the proposal markdown is handed over as deltas while the provider writes.
   * Unconfigured providers and invalid input throw before any stream starts;
   * a client abort persists nothing. See `proposal_streaming.ts` for the
   * frame vocabulary and the session-owned in-flight permit.
   */
  draftProposalStream(
    principal: Principal,
    projectId: string,
    documentId: string,
    input: ProposalDraftInput,
    reportCleanupFailure: ProviderCleanupFailureReporter,
    signal?: AbortSignal,
  ): ProposalStreamSession {
    return streamProposal(this.pipeline, {
      principal,
      projectId,
      documentId,
      input,
      reportCleanupFailure,
      signal,
    });
  }

  /**
   * Accept a completed proposal: gated (completed status, non-empty
   * proposal), idempotent (an accepted job returns unchanged), and the
   * accepted revision carries source `ai-accepted` with `metadata.ai_job_id`.
   */
  adoptProposal(principal: Principal, projectId: string, jobId: string): Record<string, unknown> {
    return jobPayload(
      this.proposalAcceptance.acceptCompletedProposal(
        scopeForPrincipal(principal),
        projectId,
        jobId,
        this.now(),
      ),
    );
  }
}
