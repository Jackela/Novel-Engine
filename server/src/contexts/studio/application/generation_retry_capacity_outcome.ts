import { ERROR_CODES } from "../../../shared/domain/error_codes.js";
import { GenerationCapacityExceededError } from "../domain/exceptions.js";
import { GENERATION_PROMPT_BYTE_LIMIT } from "../domain/generation_capacity_policy.js";
import type { JobRecord, MarkJobOutcomeInput } from "./ports/job_records.js";
import {
  CAPACITY_ERROR_KEY,
  type CapacityOutcomeEvidence,
  capacityRetryOutcome,
  isCapacityEvidenceRecord,
  type RetryCapacityOutcomeProtocol,
  replayCapacityOutcome,
} from "./retry_capacity_outcome_shared.js";

const CAPACITY_ERROR_CODE = ERROR_CODES.GENERATION_CAPACITY_EXCEEDED;
const CAPACITY_MESSAGE = "Generation capacity exceeded.";

/**
 * The closed shapes of this protocol's retained outcome. Writer construction
 * and recognizer matching share these key lists: `buildFailureResult` is
 * exhaustive and closed over them via `satisfies`, so a writer-side shape
 * tweak cannot compile (or pass the round-trip contract test) without the
 * recognizer's exact-key match moving with it.
 */
const RESULT_KEYS = Object.freeze([
  "accepted_revision_id",
  "base_revision_id",
  CAPACITY_ERROR_KEY,
  "proposal_markdown",
] as const);

type CapacityResult = Record<(typeof RESULT_KEYS)[number], unknown>;

interface GenerationCapacityEvidence extends CapacityOutcomeEvidence {
  readonly code: typeof CAPACITY_ERROR_CODE;
  readonly resource: "prompt_bytes";
}

/**
 * Generation admission pins the one configured prompt-byte budget: only the
 * exact `prompt_bytes` limit/excess pair is recognized as replayable capacity
 * evidence.
 */
function isGenerationCapacityEvidence(value: unknown): value is GenerationCapacityEvidence {
  if (!isCapacityEvidenceRecord(value)) return false;
  return (
    value.code === CAPACITY_ERROR_CODE &&
    value.resource === "prompt_bytes" &&
    value.limit === GENERATION_PROMPT_BYTE_LIMIT &&
    value.observed === GENERATION_PROMPT_BYTE_LIMIT + 1
  );
}

const PROTOCOL: RetryCapacityOutcomeProtocol<
  GenerationCapacityEvidence,
  GenerationCapacityExceededError
> = {
  jobKind: "proposal",
  capacityErrorCode: CAPACITY_ERROR_CODE,
  capacityMessage: CAPACITY_MESSAGE,
  resultKeys: RESULT_KEYS,
  readRequestIdentity(request) {
    const baseRevisionId = request.base_revision_id;
    if (typeof baseRevisionId !== "string") {
      throw new Error("Capacity-failed proposal retry is missing its persisted base revision.");
    }
    return baseRevisionId;
  },
  buildFailureResult(baseRevisionId, evidence) {
    return {
      proposal_markdown: "",
      base_revision_id: baseRevisionId,
      accepted_revision_id: null,
      [CAPACITY_ERROR_KEY]: evidence,
    } satisfies CapacityResult;
  },
  isFailedResultShape(result) {
    return (
      result.proposal_markdown === "" &&
      typeof result.base_revision_id === "string" &&
      result.accepted_revision_id === null
    );
  },
  isCapacityEvidence: isGenerationCapacityEvidence,
  rebuildCapacityError(evidence) {
    return new GenerationCapacityExceededError(
      evidence.resource,
      evidence.limit,
      evidence.observed,
    );
  },
};

/** Build the atomic failed outcome retained by a permanent proposal retry refusal. */
export function generationRetryCapacityOutcome(
  retry: JobRecord,
  error: GenerationCapacityExceededError,
  now: Date,
): MarkJobOutcomeInput {
  return capacityRetryOutcome(PROTOCOL, retry, error, now);
}

/** Rebuild only the exact structured terminal outcome owned by this protocol. */
export function replayedGenerationCapacityError(
  job: JobRecord,
): GenerationCapacityExceededError | null {
  return replayCapacityOutcome(PROTOCOL, job);
}
