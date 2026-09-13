import {
  EXPORT_CAPACITY_RESOURCES,
  ExportCapacityExceededError,
  type ExportCapacityResource,
} from "../domain/exceptions.js";
import { isExportArtifactFormat } from "./export_artifact_identity.js";
import type { JobRecord, MarkJobOutcomeInput } from "./ports/job_records.js";
import {
  CAPACITY_ERROR_KEY,
  type CapacityOutcomeEvidence,
  capacityRetryOutcome,
  isCapacityEvidenceRecord,
  type RetryCapacityOutcomeProtocol,
  replayCapacityOutcome,
} from "./retry_capacity_outcome_shared.js";

const CAPACITY_ERROR_CODE = "EXPORT_CAPACITY_EXCEEDED";
const CAPACITY_MESSAGE = "Export capacity exceeded.";

/**
 * The closed shapes of this protocol's retained outcome. Writer construction
 * and recognizer matching share these key lists: `buildFailureResult` is
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

type CapacityResult = Record<(typeof RESULT_KEYS)[number], unknown>;

interface ExportCapacityEvidence extends CapacityOutcomeEvidence {
  readonly code: typeof CAPACITY_ERROR_CODE;
  readonly resource: ExportCapacityResource;
}

function isCapacityResource(value: unknown): value is ExportCapacityResource {
  return (
    typeof value === "string" && EXPORT_CAPACITY_RESOURCES.some((resource) => resource === value)
  );
}

/**
 * Export admission accepts any known export resource carrying a bounded
 * safe-integer limit whose observed value is exactly limit + 1; the concrete
 * budget is not pinned here because each export phase owns its own limit.
 */
function isExportCapacityEvidence(value: unknown): value is ExportCapacityEvidence {
  if (!isCapacityEvidenceRecord(value)) return false;
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

const PROTOCOL: RetryCapacityOutcomeProtocol<ExportCapacityEvidence, ExportCapacityExceededError> =
  {
    jobKind: "export",
    capacityErrorCode: CAPACITY_ERROR_CODE,
    capacityMessage: CAPACITY_MESSAGE,
    resultKeys: RESULT_KEYS,
    readRequestIdentity(request) {
      const format = request.format;
      if (!isExportArtifactFormat(format)) {
        throw new Error("Capacity-failed export retry is missing its persisted format.");
      }
      return format;
    },
    buildFailureResult(format, evidence) {
      return {
        export_id: null,
        snapshot_id: null,
        format,
        download_url: null,
        [CAPACITY_ERROR_KEY]: evidence,
      } satisfies CapacityResult;
    },
    isFailedResultShape(result) {
      return (
        result.export_id === null &&
        result.snapshot_id === null &&
        result.download_url === null &&
        isExportArtifactFormat(result.format)
      );
    },
    isCapacityEvidence: isExportCapacityEvidence,
    rebuildCapacityError(evidence) {
      return new ExportCapacityExceededError(evidence.resource, evidence.limit, evidence.observed);
    },
  };

/** Build the one atomic failed outcome retained by a permanent export retry refusal. */
export function exportRetryCapacityOutcome(
  retry: JobRecord,
  error: ExportCapacityExceededError,
  now: Date,
): MarkJobOutcomeInput {
  return capacityRetryOutcome(PROTOCOL, retry, error, now);
}

/** Rebuild only the exact structured terminal outcome owned by this protocol. */
export function replayedExportCapacityError(job: JobRecord): ExportCapacityExceededError | null {
  return replayCapacityOutcome(PROTOCOL, job);
}
