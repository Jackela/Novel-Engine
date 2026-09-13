import { dumpJson, safeLoadJson } from "./payloads.js";
import type { JobRecord, MarkJobOutcomeInput } from "./ports/job_records.js";

export const CAPACITY_ERROR_KEY = "capacity_error";
const EVENT_DETAIL_KEYS = Object.freeze(["error", CAPACITY_ERROR_KEY] as const);
const EVIDENCE_KEYS = Object.freeze(["code", "limit", "observed", "resource"] as const);

type CapacityEventDetails = Record<(typeof EVENT_DETAIL_KEYS)[number], unknown>;

/** The structured evidence envelope both retry-capacity protocols retain. */
export interface CapacityOutcomeEvidence {
  readonly code: string;
  readonly resource: string;
  readonly limit: number;
  readonly observed: number;
}

/** The structural refusal shape shared by the studio capacity error classes. */
export interface CapacityRefusal {
  readonly message: string;
  readonly resource: string;
  readonly limit: number;
  readonly observed: number;
}

/**
 * One retry-capacity protocol's admission policy. The evidence predicate and
 * the failure-shape predicate encode each protocol's own admission semantics
 * and are deliberately not unified: generation pins the single configured
 * prompt-byte budget, export admits any bounded export-resource excess. The
 * shared skeleton only owns the identical envelope, gating, and JSON plumbing.
 */
export interface RetryCapacityOutcomeProtocol<
  E extends CapacityOutcomeEvidence,
  Err extends CapacityRefusal,
> {
  /** The job kind whose failed retries this protocol recognizes. */
  readonly jobKind: string;
  readonly capacityErrorCode: string;
  readonly capacityMessage: string;
  /** Exact stored-result key list; must already be sorted (see `hasExactKeys`). */
  readonly resultKeys: readonly string[];
  /** Extract and validate the persisted request identity; throws when absent. */
  readRequestIdentity(request: Record<string, unknown>): string;
  buildFailureResult(identity: string, evidence: CapacityOutcomeEvidence): Record<string, unknown>;
  /** Admission check over the stored failure result's own fields. */
  isFailedResultShape(result: Record<string, unknown>): boolean;
  /** Per-protocol evidence admission (see the interface doc above). */
  isCapacityEvidence(value: unknown): value is E;
  rebuildCapacityError(evidence: E): Err;
}

/** Build the atomic failed outcome retained by a permanent retry refusal. */
export function capacityRetryOutcome<
  E extends CapacityOutcomeEvidence,
  Err extends CapacityRefusal,
>(
  protocol: RetryCapacityOutcomeProtocol<E, Err>,
  retry: JobRecord,
  error: Err,
  now: Date,
): MarkJobOutcomeInput {
  const request = safeLoadJson(retry.requestJson);
  const identity = protocol.readRequestIdentity(request);
  const evidence = capacityEvidence(error, protocol.capacityErrorCode);
  return {
    status: "failed",
    resultJson: dumpJson(protocol.buildFailureResult(identity, evidence)),
    error: error.message,
    eventDetailsJson: dumpJson(capacityEventDetails(error.message, evidence)),
    now,
  };
}

/** Rebuild only the exact structured terminal outcome owned by this protocol. */
export function replayCapacityOutcome<
  E extends CapacityOutcomeEvidence,
  Err extends CapacityRefusal,
>(protocol: RetryCapacityOutcomeProtocol<E, Err>, job: JobRecord): Err | null {
  if (
    job.kind !== protocol.jobKind ||
    job.status !== "failed" ||
    job.retryOfJobId === null ||
    job.error !== protocol.capacityMessage
  ) {
    return null;
  }
  const result = parseObject(job.resultJson);
  if (result === null || !hasExactKeys(result, protocol.resultKeys)) return null;
  if (!protocol.isFailedResultShape(result)) return null;
  const evidence = result[CAPACITY_ERROR_KEY];
  if (!protocol.isCapacityEvidence(evidence)) return null;
  return protocol.rebuildCapacityError(evidence);
}

/**
 * The exact-key envelope every evidence record must satisfy. Per-protocol
 * value admission (code, resource, limit/observed relation) stays in each
 * protocol's own `isCapacityEvidence`.
 */
export function isCapacityEvidenceRecord(value: unknown): value is CapacityOutcomeEvidence {
  return isObject(value) && hasExactKeys(value, EVIDENCE_KEYS);
}

function capacityEvidence(error: CapacityRefusal, code: string): CapacityOutcomeEvidence {
  return { code, resource: error.resource, limit: error.limit, observed: error.observed };
}

function capacityEventDetails(
  message: string,
  evidence: CapacityOutcomeEvidence,
): CapacityEventDetails {
  return {
    error: message,
    [CAPACITY_ERROR_KEY]: evidence,
  } satisfies CapacityEventDetails;
}

function parseObject(value: string): Record<string, unknown> | null {
  try {
    const parsed: unknown = JSON.parse(value);
    return isObject(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

/** Exact-key match; `keys` must already be sorted like `Object.keys().sort()`. */
function hasExactKeys(value: Record<string, unknown>, keys: readonly string[]): boolean {
  const actual = Object.keys(value).sort();
  return actual.length === keys.length && actual.every((key, index) => key === keys[index]);
}
