import {
  isTextProviderName,
  type ProviderStep,
  type TextProviderName,
} from "../../../contexts/ai/application/ports/text_generation.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import type { InFlightOperationPermit } from "./operation_in_flight.js";
import { dumpJson } from "./payloads.js";
import type { JobRecord } from "./ports/job_records.js";
import type { ProposalContextSource } from "./ports/proposal_context_store.js";
import type { ProjectScope } from "./ports/studio_store.js";
import { OPERATION_STEPS, type ProposalJobSeed } from "./proposal_landing.js";
import type { ProviderCleanupFailureReporter } from "./provider_disposal.js";

/**
 * The request/admission half of the proposal pipeline shared by the
 * synchronous draft (#305), the streaming twin (#308), and the retry path
 * (#272): transport-decoded request types, operation/provider admission,
 * captured-revision resolution, and the seed construction that lands on every
 * proposal job. The execution sequence lives in `proposal_pipeline.ts`.
 */

/** The provider-facing task target, resolved before any job row exists. */
export interface ProposalRevisionTarget {
  readonly document: ProposalContextSource["target"];
  readonly revision: NonNullable<ProposalContextSource["target"]["currentRevision"]>;
}

/** Resolves the exact target revision already paired inside a captured context. */
export function proposalRevisionFromContext(
  context: ProposalContextSource,
): ProposalRevisionTarget {
  const revision = context.target.currentRevision;
  if (revision === null) {
    throw new InvalidOperationError("Document has no current revision.");
  }
  return { document: context.target, revision };
}

/** Rejects unsupported providers before any work is performed. */
export function admitTextProvider(provider: string): TextProviderName {
  if (!isTextProviderName(provider)) {
    throw new InvalidOperationError(`Unsupported text generation provider: ${provider}`);
  }
  return provider;
}

/** Maps an API operation onto its provider-facing step, or undefined. */
export function proposalStepForOperation(operation: string): ProviderStep | undefined {
  return OPERATION_STEPS[operation];
}

/** Rejects unknown operations and providers before any work is performed. */
export function admitProposalOperation(
  operation: string,
  provider: string,
): { step: ProviderStep; providerName: TextProviderName } {
  const step = proposalStepForOperation(operation);
  if (step === undefined) {
    throw new InvalidOperationError(`Unsupported proposal operation: ${operation}`);
  }
  return { step, providerName: admitTextProvider(provider) };
}

/** Builds the job seed (including the request evidence JSON) for landing. */
export function buildProposalSeed(params: {
  readonly projectId: string;
  readonly documentId: string;
  readonly operation: string;
  readonly provider: TextProviderName;
  readonly instruction: string;
  readonly baseRevisionId: string;
  readonly now: Date;
}): ProposalJobSeed {
  return {
    projectId: params.projectId,
    documentId: params.documentId,
    operation: params.operation,
    provider: params.provider,
    requestJson: dumpJson({
      operation: params.operation,
      instruction: params.instruction,
      base_revision_id: params.baseRevisionId,
    }),
    now: params.now,
  };
}

/** One proposal generation request, decoded from its transport and scoped. */
export interface ProposalGenerationRequest {
  readonly scope: ProjectScope;
  readonly projectId: string;
  readonly documentId: string;
  readonly operation: string;
  readonly instruction: string;
  readonly provider: string;
}

/** Streaming-only options: cleanup reporting, abort, and permit handoff. */
export interface ProposalStreamOptions {
  readonly reportCleanupFailure: ProviderCleanupFailureReporter;
  /** Aborted when the client disconnects: the stream ends with no job. */
  readonly signal?: AbortSignal | undefined;
  /** Receives the acquired permit; the caller owns its session-scoped release. */
  readonly ownPermit: (permit: InFlightOperationPermit) => void;
}

/** A claimed proposal retry row plus the scope executing it. The clock keeps
 * every timestamp on the retry chain (claim, outcomes, landing) sourced from
 * the single JobRetryExecutor injection point. */
export interface ProposalRetryRequest {
  readonly scope: ProjectScope;
  readonly retry: JobRecord;
  readonly reportCleanupFailure: ProviderCleanupFailureReporter;
  readonly now: () => Date;
}
