import type { Principal } from "../../../shared/application/ports/auth.js";
import type { InFlightOperationPermit } from "./operation_in_flight.js";
import type { ProposalStreamFramePayload } from "./payload_schemas/proposal_frame.js";
import { scopeForPrincipal } from "./ports/studio_store.js";
import type { ProposalGenerationRequest } from "./proposal_admission.js";
import type { ProviderCleanupFailureReporter } from "./proposal_landing.js";
import type { ProposalGenerationPipeline } from "./proposal_pipeline.js";

/**
 * The terminal frame vocabulary of a streamed proposal (#308), declared as
 * the TypeBox SSE-frame SSOT in `payload_schemas/proposal_frame.ts` (#440):
 * the pipeline generator types its yields with the same `Static` shape the
 * drift guard pins and the HTTP surface serializes verbatim.
 */
export type ProposalStreamFrame = ProposalStreamFramePayload;

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
 * The streaming proposal session (#308): the execution sequence (validation,
 * in-flight guarding, generation, and job/usage landing) lives in the
 * pipeline; this session owns only the transport-facing frame stream and the
 * in-flight permit's session-scoped release. Invalid input, unknown documents,
 * an in-flight conflict, and providers without the streaming capability throw
 * before any delta — the HTTP surface answers with the normal error envelope.
 * Once the stream runs, provider failures land a failed job exactly like the
 * synchronous path and end the stream with one error frame. A client abort
 * persists nothing at all.
 */
export interface ProposalStreamSession {
  readonly frames: AsyncGenerator<ProposalStreamFrame, void, void>;
  releaseCapacity(): void;
}

export function streamProposal(
  pipeline: ProposalGenerationPipeline,
  request: ProposalStreamRequest,
): ProposalStreamSession {
  let permit: InFlightOperationPermit | undefined;
  let released = false;
  const generation: ProposalGenerationRequest = {
    scope: scopeForPrincipal(request.principal),
    projectId: request.projectId,
    documentId: request.documentId,
    operation: request.input.operation,
    instruction: request.input.instruction,
    provider: request.input.provider,
  };
  const frames = pipeline.stream(generation, {
    reportCleanupFailure: request.reportCleanupFailure,
    signal: request.signal,
    ownPermit: (acquired) => {
      permit = acquired;
    },
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
