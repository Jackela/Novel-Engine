import {
  type TextGenerationProvider,
  TextGenerationProviderError,
  type TextGenerationProviderFactory,
} from "../../../contexts/ai/application/ports/text_generation.js";
import type { Principal } from "../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import { NotFoundError } from "../domain/exceptions.js";
import type { DocumentService } from "./document_service.js";
import type { InFlightOperationGuard } from "./operation_in_flight.js";
import { dumpJson, jobPayload, safeLoadJson } from "./payloads.js";
import {
  buildProposalTask,
  completedProposalJob,
  disposeProvider,
  failedProposalJob,
  type ProviderCleanupFailureReporter,
  validatedProposalOrThrow,
} from "./proposal_landing.js";
import { buildProposalSeed, validateProposalRequest } from "./proposal_pipeline.js";

export {
  INVALID_PROPOSAL_PROSE,
  OPERATION_STEPS,
  resolvedTokenCount,
  SYSTEM_PROMPT,
} from "./proposal_landing.js";

import type { StudioStore } from "./ports/studio_store.js";
import { scopeForPrincipal } from "./ports/studio_store.js";
import type { ProposalStreamFrame } from "./proposal_streaming.js";
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
  private readonly documents: DocumentService;
  private readonly providerFactory: TextGenerationProviderFactory;
  private readonly inFlight: InFlightOperationGuard;
  private readonly now: () => Date;

  constructor(
    store: StudioStore,
    documents: DocumentService,
    providerFactory: TextGenerationProviderFactory,
    inFlight: InFlightOperationGuard,
    now: () => Date = () => new Date(),
  ) {
    this.store = store;
    this.documents = documents;
    this.providerFactory = providerFactory;
    this.inFlight = inFlight;
    this.now = now;
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
    const { step, providerName, operation, instruction, document, revision } =
      validateProposalRequest(this.store, scope, projectId, documentId, input);
    // #305: the provider call runs before any job row exists, so identical
    // concurrent submissions are deduplicated by the in-flight guard — the
    // loser receives a 409 instead of running the work twice.
    const inFlightTarget = {
      projectId,
      documentId,
      operation,
    };
    this.inFlight.enter(inFlightTarget);

    const seed = buildProposalSeed({
      projectId,
      documentId,
      operation,
      provider: providerName,
      instruction,
      baseRevisionId: revision.id,
      now: this.now(),
    });
    let provider: TextGenerationProvider | undefined;

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
    } finally {
      this.inFlight.exit(inFlightTarget);
      if (provider !== undefined) {
        await disposeProvider(provider, reportCleanupFailure);
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
  ): AsyncGenerator<ProposalStreamFrame, void, void> {
    return streamProposal(
      {
        store: this.store,
        providerFactory: this.providerFactory,
        inFlight: this.inFlight,
        now: this.now,
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
    const scope = scopeForPrincipal(principal);
    const job = this.store.findJob(scope, projectId, jobId);
    if (job.kind !== "proposal" || job.documentId === null) {
      // A job of another kind is not a proposal at this address (Python: NotFound).
      throw new NotFoundError(
        `No AI proposal job '${jobId}' exists in project '${projectId}': the id does not ` +
          `exist there, or the job belongs to a different project.`,
      );
    }
    if (job.status !== "completed") {
      throw new InvalidOperationError("Only a completed proposal can be accepted.");
    }
    const result = safeLoadJson(job.resultJson);
    if (result.accepted_revision_id) {
      return jobPayload(job);
    }
    const proposal = typeof result.proposal_markdown === "string" ? result.proposal_markdown : "";
    if (proposal.trim() === "") {
      throw new InvalidOperationError("Only a completed proposal with content can be accepted.");
    }
    const request = safeLoadJson(job.requestJson);
    const baseRevisionId =
      typeof request.base_revision_id === "string" ? request.base_revision_id : null;
    const saved = this.documents.storeDocument(principal, projectId, job.documentId, {
      contentMarkdown: proposal,
      baseRevisionId,
      metadata: { ai_job_id: job.id },
      source: "ai-accepted",
    });
    const updated = this.store.setJobResult(
      scope,
      projectId,
      job.id,
      dumpJson({ ...result, accepted_revision_id: saved.current_revision_id }),
      this.now(),
    );
    return jobPayload(updated);
  }
}
