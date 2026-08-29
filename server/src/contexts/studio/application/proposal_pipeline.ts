import {
  isTextProviderName,
  type ProviderStep,
  type TextProviderName,
} from "../../../contexts/ai/application/ports/text_generation.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import { dumpJson } from "./payloads.js";
import type {
  DocumentWithCurrent,
  ProjectScope,
  RevisionRecord,
  StudioStore,
} from "./ports/studio_store.js";
import { OPERATION_STEPS, type ProposalJobSeed } from "./proposal_landing.js";

/**
 * The request/validation half of the proposal pipeline shared by the
 * synchronous draft (#305), the streaming twin (#308), and the retry path
 * (#272): operation/provider admission, document+revision resolution, and
 * the seed construction that lands on every proposal job. The outcome half
 * (provider task, prose judgment, completed/failed landing) lives in
 * `proposal_landing.ts`; keeping the two halves here means no entry point
 * carries its own copy of the orchestration.
 */

/** The admitted request shape every entry point works from. */
export interface ValidatedProposalRequest {
  readonly step: ProviderStep;
  readonly providerName: TextProviderName;
  readonly operation: string;
  readonly instruction: string;
  readonly document: DocumentWithCurrent;
  readonly revision: RevisionRecord;
}

/** The provider-facing task target, resolved before any job row exists. */
export interface ProposalRevisionTarget {
  readonly document: DocumentWithCurrent;
  readonly revision: RevisionRecord;
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

/**
 * Resolves the document and its current revision. A document without a
 * current revision cannot host a proposal generation.
 */
export function resolveProposalRevision(
  store: StudioStore,
  scope: ProjectScope,
  projectId: string,
  documentId: string,
): ProposalRevisionTarget {
  const document = store.findDocument(scope, projectId, documentId);
  const revision = document.currentRevision;
  if (revision === null) {
    throw new InvalidOperationError("Document has no current revision.");
  }
  return { document, revision };
}

/** Validates a user-supplied draft/stream request end to end. */
export function validateProposalRequest(
  store: StudioStore,
  scope: ProjectScope,
  projectId: string,
  documentId: string,
  input: { readonly operation: string; readonly instruction: string; readonly provider: string },
): ValidatedProposalRequest {
  const { step, providerName } = admitProposalOperation(input.operation, input.provider);
  const { document, revision } = resolveProposalRevision(store, scope, projectId, documentId);
  return {
    step,
    providerName,
    operation: input.operation,
    instruction: input.instruction,
    document,
    revision,
  };
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
