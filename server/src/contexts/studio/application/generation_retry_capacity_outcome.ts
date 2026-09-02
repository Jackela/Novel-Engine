import { ERROR_CODES } from "../../../shared/domain/error_codes.js";
import { GenerationCapacityExceededError } from "../domain/exceptions.js";
import { GENERATION_PROMPT_BYTE_LIMIT } from "../domain/generation_capacity_policy.js";
import { dumpJson, safeLoadJson } from "./payloads.js";
import type { JobRecord, MarkJobOutcomeInput } from "./ports/studio_store.js";

const CAPACITY_ERROR_CODE = ERROR_CODES.GENERATION_CAPACITY_EXCEEDED;
const CAPACITY_ERROR_KEY = "capacity_error";
const CAPACITY_MESSAGE = "Generation capacity exceeded.";

interface GenerationCapacityEvidence {
  readonly code: typeof CAPACITY_ERROR_CODE;
  readonly resource: "prompt_bytes";
  readonly limit: number;
  readonly observed: number;
}

/** Build the atomic failed outcome retained by a permanent proposal retry refusal. */
export function generationRetryCapacityOutcome(
  retry: JobRecord,
  error: GenerationCapacityExceededError,
  now: Date,
): MarkJobOutcomeInput {
  const request = safeLoadJson(retry.requestJson);
  const baseRevisionId = request.base_revision_id;
  if (typeof baseRevisionId !== "string") {
    throw new Error("Capacity-failed proposal retry is missing its persisted base revision.");
  }
  const evidence = capacityEvidence(error);
  return {
    status: "failed",
    resultJson: dumpJson({
      proposal_markdown: "",
      base_revision_id: baseRevisionId,
      accepted_revision_id: null,
      [CAPACITY_ERROR_KEY]: evidence,
    }),
    error: error.message,
    eventDetailsJson: dumpJson({ error: error.message, [CAPACITY_ERROR_KEY]: evidence }),
    now,
  };
}

/** Rebuild only the exact structured terminal outcome owned by this protocol. */
export function replayedGenerationCapacityError(
  job: JobRecord,
): GenerationCapacityExceededError | null {
  if (
    job.kind !== "proposal" ||
    job.status !== "failed" ||
    job.retryOfJobId === null ||
    job.error !== CAPACITY_MESSAGE
  ) {
    return null;
  }
  const result = parseObject(job.resultJson);
  if (result === null || !hasExactKeys(result, RESULT_KEYS)) return null;
  if (
    result.proposal_markdown !== "" ||
    typeof result.base_revision_id !== "string" ||
    result.accepted_revision_id !== null
  ) {
    return null;
  }
  const evidence = result[CAPACITY_ERROR_KEY];
  if (!isCapacityEvidence(evidence)) return null;
  return new GenerationCapacityExceededError(evidence.resource, evidence.limit, evidence.observed);
}

const RESULT_KEYS = Object.freeze([
  "accepted_revision_id",
  "base_revision_id",
  CAPACITY_ERROR_KEY,
  "proposal_markdown",
]);
const EVIDENCE_KEYS = Object.freeze(["code", "limit", "observed", "resource"]);

function capacityEvidence(error: GenerationCapacityExceededError): GenerationCapacityEvidence {
  return {
    code: CAPACITY_ERROR_CODE,
    resource: error.resource,
    limit: error.limit,
    observed: error.observed,
  };
}

function parseObject(value: string): Record<string, unknown> | null {
  try {
    const parsed: unknown = JSON.parse(value);
    return isObject(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function isCapacityEvidence(value: unknown): value is GenerationCapacityEvidence {
  if (!isObject(value) || !hasExactKeys(value, EVIDENCE_KEYS)) return false;
  return (
    value.code === CAPACITY_ERROR_CODE &&
    value.resource === "prompt_bytes" &&
    value.limit === GENERATION_PROMPT_BYTE_LIMIT &&
    value.observed === GENERATION_PROMPT_BYTE_LIMIT + 1
  );
}

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasExactKeys(value: Record<string, unknown>, keys: readonly string[]): boolean {
  const actual = Object.keys(value).sort();
  return actual.length === keys.length && actual.every((key, index) => key === keys[index]);
}
