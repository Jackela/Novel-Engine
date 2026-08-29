import {
  type TextGenerationProvider,
  TextGenerationProviderError,
  type TextGenerationProviderFactory,
  type TextGenerationStreamOutcome,
} from "../../../contexts/ai/application/ports/text_generation.js";
import type { Principal } from "../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import type { InFlightOperationGuard } from "./operation_in_flight.js";
import { jobPayload } from "./payloads.js";
import type { StudioStore } from "./ports/studio_store.js";
import { scopeForPrincipal } from "./ports/studio_store.js";
import {
  buildProposalTask,
  completedProposalJob,
  disposeProvider,
  failedProposalJob,
  type ProviderCleanupFailureReporter,
  validatedProposalOrThrow,
} from "./proposal_landing.js";
import { buildProposalSeed, validateProposalRequest } from "./proposal_pipeline.js";

/** The terminal frame vocabulary of a streamed proposal (#308). */
export type ProposalStreamFrame =
  | { readonly type: "delta"; readonly text: string }
  | { readonly type: "done"; readonly job: Record<string, unknown> }
  | { readonly type: "error"; readonly error: ProposalStreamError };

/** In-stream failures carry the failed-job message; codes stay closed. */
export interface ProposalStreamError {
  readonly code: "PROVIDER_FAILED";
  readonly message: string;
}

export interface ProposalStreamDeps {
  readonly store: StudioStore;
  readonly providerFactory: TextGenerationProviderFactory;
  readonly inFlight: InFlightOperationGuard;
  readonly now: () => Date;
}

export interface ProposalStreamRequest {
  readonly principal: Principal;
  readonly projectId: string;
  readonly documentId: string;
  readonly input: {
    readonly operation: string;
    readonly instruction: string;
    readonly provider: string;
  };
  readonly reportCleanupFailure: ProviderCleanupFailureReporter;
  /** Aborted when the client disconnects: the stream ends with no job. */
  readonly signal?: AbortSignal | undefined;
}

/**
 * The streaming proposal pipeline (#308): validation, in-flight guarding, and
 * the job/usage landing match the synchronous draft byte-for-byte, but the
 * proposal markdown flows out as deltas while the provider writes. Invalid
 * input, unknown documents, an in-flight conflict, and providers without the
 * streaming capability throw before any delta — the HTTP surface answers
 * with the normal error envelope. Once the stream runs, provider failures
 * (connect, mid-stream, or prose rejected after completion) land a failed
 * job exactly like the synchronous path and end the stream with one error
 * frame. A client abort persists nothing at all.
 */
export async function* streamProposal(
  deps: ProposalStreamDeps,
  request: ProposalStreamRequest,
): AsyncGenerator<ProposalStreamFrame, void, void> {
  const { input, projectId, documentId } = request;
  const scope = scopeForPrincipal(request.principal);
  const { step, providerName, operation, instruction, document, revision } =
    validateProposalRequest(deps.store, scope, projectId, documentId, input);
  const seed = buildProposalSeed({
    projectId,
    documentId,
    operation,
    provider: providerName,
    instruction,
    baseRevisionId: revision.id,
    now: deps.now(),
  });
  // #305 parity: identical concurrent submissions are deduplicated by the
  // in-flight guard — the loser receives a 409 instead of running work twice.
  const inFlightTarget = { projectId, documentId, operation };
  deps.inFlight.enter(inFlightTarget);
  let provider: TextGenerationProvider | undefined;
  try {
    provider = deps.providerFactory(providerName);
    const stream = provider.generateStructuredStreaming?.bind(provider);
    if (stream === undefined) {
      throw new InvalidOperationError(
        `Provider '${providerName}' does not support streaming generation.`,
      );
    }
    let accumulated = "";
    let reported: TextGenerationStreamOutcome | undefined;
    for await (const delta of stream(
      buildProposalTask(
        step,
        operation,
        instruction,
        deps.store,
        scope,
        projectId,
        document,
        revision,
      ),
      {
        signal: request.signal,
        onOutcome: (value) => {
          reported = value;
        },
      },
    )) {
      accumulated += delta;
      yield { type: "delta", text: delta };
    }
    if (request.signal?.aborted === true) return;
    const { proposal } = validatedProposalOrThrow({ content: { chapter_markdown: accumulated } });
    yield {
      type: "done",
      job: jobPayload(
        completedProposalJob(deps.store, scope, seed, revision.id, {
          proposal,
          provider: providerName,
          model: reported?.model ?? "",
          promptTokens: reported?.promptTokens ?? null,
          completionTokens: reported?.completionTokens ?? null,
          instruction,
        }),
      ),
    };
  } catch (error) {
    if (request.signal?.aborted === true) return;
    if (!(error instanceof TextGenerationProviderError)) {
      throw error;
    }
    failedProposalJob(deps.store, scope, seed, revision.id, error.message);
    yield { type: "error", error: { code: "PROVIDER_FAILED", message: error.message } };
  } finally {
    deps.inFlight.exit(inFlightTarget);
    if (provider !== undefined) {
      await disposeProvider(provider, request.reportCleanupFailure);
    }
  }
}
