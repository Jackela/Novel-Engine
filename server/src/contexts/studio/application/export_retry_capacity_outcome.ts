import {
  EXPORT_CAPACITY_RESOURCES,
  ExportCapacityExceededError,
  type ExportCapacityResource,
} from "../domain/exceptions.js";
import { isExportArtifactFormat } from "./export_artifact_identity.js";
import { dumpJson, safeLoadJson } from "./payloads.js";
import type { JobRecord, MarkJobOutcomeInput } from "./ports/job_records.js";

const CAPACITY_ERROR_CODE = "EXPORT_CAPACITY_EXCEEDED";
const CAPACITY_ERROR_KEY = "capacity_error";
const CAPACITY_MESSAGE = "Export capacity exceeded.";

/**
 * The closed shapes of this protocol's retained outcome. Writer construction
 * and recognizer matching share these key lists: the builders below are
 * exhaustive and closed over them via `satisfies`, so a writer-side shape
 * tweak cannot compile (or pass the round-trip contract test) without the
 * recognizer's exact-key match moving with it.
 */
const RESULT_KEYS = Object.freeze([
  CAPACITY_ERROR_KEY,
  "download_url",
  "export_id",
  "format",
  "snapshot_id",
] as const);
const EVENT_DETAIL_KEYS = Object.freeze(["error", CAPACITY_ERROR_KEY] as const);
const EVIDENCE_KEYS = Object.freeze(["code", "limit", "observed", "resource"] as const);

type CapacityResult = Record<(typeof RESULT_KEYS)[number], unknown>;
type CapacityEventDetails = Record<(typeof EVENT_DETAIL_KEYS)[number], unknown>;
type CapacityEvidenceRecord = Record<(typeof EVIDENCE_KEYS)[number], unknown>;

interface CapacityEvidence {
  readonly code: typeof CAPACITY_ERROR_CODE;
  readonly resource: ExportCapacityResource;
  readonly limit: number;
  readonly observed: number;
}

/** Build the one atomic failed outcome retained by a permanent export retry refusal. */
export function exportRetryCapacityOutcome(
  retry: JobRecord,
  error: ExportCapacityExceededError,
  now: Date,
): MarkJobOutcomeInput {
  const request = safeLoadJson(retry.requestJson);
  const format = request.format;
  if (!isExportArtifactFormat(format)) {
    throw new Error("Capacity-failed export retry is missing its persisted format.");
  }
  const evidence = capacityEvidence(error);
  return {
    status: "failed",
    resultJson: dumpJson(capacityResult(format, evidence)),
    error: error.message,
    eventDetailsJson: dumpJson(capacityEventDetails(error.message, evidence)),
    now,
  };
}

/** Rebuild only the exact structured terminal outcome owned by this protocol. */
export function replayedExportCapacityError(job: JobRecord): ExportCapacityExceededError | null {
  if (
    job.kind !== "export" ||
    job.status !== "failed" ||
    job.retryOfJobId === null ||
    job.error !== CAPACITY_MESSAGE
  ) {
    return null;
  }
  const result = parseObject(job.resultJson);
  if (result === null || !hasExactKeys(result, RESULT_KEYS)) return null;
  if (
    result.export_id !== null ||
    result.snapshot_id !== null ||
    result.download_url !== null ||
    !isExportArtifactFormat(result.format)
  ) {
    return null;
  }
  const evidence = result[CAPACITY_ERROR_KEY];
  if (!isCapacityEvidence(evidence)) return null;
  return new ExportCapacityExceededError(evidence.resource, evidence.limit, evidence.observed);
}

function capacityResult(format: string, evidence: CapacityEvidence): Record<string, unknown> {
  return {
    export_id: null,
    snapshot_id: null,
    format,
    download_url: null,
    [CAPACITY_ERROR_KEY]: evidence,
  } satisfies CapacityResult;
}

function capacityEventDetails(
  message: string,
  evidence: CapacityEvidence,
): Record<string, unknown> {
  return {
    error: message,
    [CAPACITY_ERROR_KEY]: evidence,
  } satisfies CapacityEventDetails;
}

function capacityEvidence(
  error: ExportCapacityExceededError,
): CapacityEvidence & CapacityEvidenceRecord {
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

function isCapacityEvidence(value: unknown): value is CapacityEvidence {
  if (!isObject(value) || !hasExactKeys(value, EVIDENCE_KEYS)) return false;
  if (value.code !== CAPACITY_ERROR_CODE || !isCapacityResource(value.resource)) return false;
  return (
    Number.isSafeInteger(value.limit) &&
    typeof value.limit === "number" &&
    value.limit >= 0 &&
    value.limit < Number.MAX_SAFE_INTEGER &&
    Number.isSafeInteger(value.observed) &&
    typeof value.observed === "number" &&
    value.observed === value.limit + 1
  );
}

function isCapacityResource(value: unknown): value is ExportCapacityResource {
  return (
    typeof value === "string" && EXPORT_CAPACITY_RESOURCES.some((resource) => resource === value)
  );
}

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasExactKeys(value: Record<string, unknown>, keys: readonly string[]): boolean {
  const actual = Object.keys(value).sort();
  return actual.length === keys.length && actual.every((key, index) => key === keys[index]);
}
