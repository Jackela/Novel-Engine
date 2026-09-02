import {
  TextGenerationCancelledError,
  type TextGenerationProvider,
  TextGenerationProviderError,
  type TextGenerationProviderFactory,
  type TextGenerationStreamOutcome,
} from "../../../contexts/ai/application/ports/text_generation.js";
import type { Principal } from "../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import type { InFlightOperationGuard, InFlightOperationPermit } from "./operation_in_flight.js";
import type { ProposalStreamFramePayload } from "./payload_schemas/proposal_frame.js";
import { jobPayload } from "./payloads.js";
import type { StudioStore } from "./ports/studio_store.js";
import { scopeForPrincipal } from "./ports/studio_store.js";
import {
  buildProposalTask,
  completedProposalJob,
  createProposalCodePointCounter,
  disposeProvider,
  failedProposalJob,
  includeProposalDelta,
  type ProviderCleanupFailureReporter,
  validatedProposalOrThrow,
} from "./proposal_landing.js";
import {
  admitProposalOperation,
  buildProposalSeed,
  proposalRevisionFromContext,
} from "./proposal_pipeline.js";

/**
 * The terminal frame vocabulary of a streamed proposal (#308), declared as
 * the TypeBox SSE-frame SSOT in `payload_schemas/proposal_frame.ts` (#440):
 * the generator types its yields with the same `Static` shape the drift
 * guard pins and the HTTP surface serializes verbatim.
 */
export type ProposalStreamFrame = ProposalStreamFramePayload;

export interface ProposalStreamDeps {
  readonly store: StudioStore;
  readonly providerFactory: TextGenerationProviderFactory;
  readonly inFlight: InFlightOperationGuard;
  readonly now: () => Date;
  /** Lorebook injection budget (#445); undefined keeps the adjudicated default. */
  readonly loreBudgetCharacters?: number | undefined;
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
export interface ProposalStreamSession {
  readonly frames: AsyncGenerator<ProposalStreamFrame, void, void>;
  releaseCapacity(): void;
}

export function streamProposal(
  deps: ProposalStreamDeps,
  request: ProposalStreamRequest,
): ProposalStreamSession {
  let permit: InFlightOperationPermit | undefined;
  let released = false;
  const frames = streamProposalFrames(deps, request, (acquired) => {
    permit = acquired;
  });
  return {
    frames,
    releaseCapacity: () => {
      if (released) return;
      released = true;
      permit?.release();
      permit = undefined;
    },
  };
}

async function* streamProposalFrames(
  deps: ProposalStreamDeps,
  request: ProposalStreamRequest,
  ownPermit: (permit: InFlightOperationPermit) => void,
): AsyncGenerator<ProposalStreamFrame, void, void> {
  const { input, projectId, documentId } = request;
  const scope = scopeForPrincipal(request.principal);
  const { step, providerName } = admitProposalOperation(input.operation, input.provider);
  const operation = input.operation;
  const instruction = input.instruction;
  // #305 parity: identical concurrent submissions are deduplicated by the
  // in-flight guard — the loser receives a 409 instead of running work twice.
  // The guard precedes row resolution so post-commit deletion cleanup keeps
  // returning the project-exclusive conflict until it actually releases.
  const inFlightTarget = { projectId, documentId, operation };
  ownPermit(deps.inFlight.acquire(inFlightTarget));
  let provider: TextGenerationProvider | undefined;
  try {
    const context = deps.store.readProposalContext(scope, projectId, documentId);
    const { revision } = proposalRevisionFromContext(context);
    const seed = buildProposalSeed({
      projectId: context.projectId,
      documentId: context.target.id,
      operation,
      provider: providerName,
      instruction,
      baseRevisionId: revision.id,
      now: deps.now(),
    });
    try {
      const task = buildProposalTask(
        step,
        operation,
        instruction,
        context,
        deps.loreBudgetCharacters,
      );
      provider = deps.providerFactory(providerName);
      const stream = provider.generateStructuredStreaming?.bind(provider);
      if (stream === undefined) {
        throw new InvalidOperationError(
          `Provider '${providerName}' does not support streaming generation.`,
        );
      }
      const accumulated: string[] = [];
      const codePoints = createProposalCodePointCounter();
      let reported: TextGenerationStreamOutcome | undefined;
      for await (const delta of stream(task, {
        signal: request.signal,
        onOutcome: (value) => {
          reported = value;
        },
      })) {
        includeProposalDelta(codePoints, delta);
        accumulated.push(delta);
        yield { type: "delta", text: delta };
      }
      if (request.signal?.aborted === true) return;
      const { proposal } = validatedProposalOrThrow({
        content: { chapter_markdown: accumulated.join("") },
      });
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
      if (error instanceof TextGenerationCancelledError) return;
      if (!(error instanceof TextGenerationProviderError)) {
        throw error;
      }
      failedProposalJob(deps.store, scope, seed, revision.id, error.message);
      yield { type: "error", error: { code: "PROVIDER_FAILED", message: error.message } };
    }
  } finally {
    if (provider !== undefined) {
      await disposeProvider(provider, request.reportCleanupFailure);
    }
  }
}
