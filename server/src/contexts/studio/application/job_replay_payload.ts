import { replayedExportCapacityError } from "./export_retry_capacity_outcome.js";
import { replayedGenerationCapacityError } from "./generation_retry_capacity_outcome.js";
import type { JobPayload } from "./payload_schemas/job.js";
import { jobPayload } from "./payloads.js";
import type { JobRecord } from "./ports/job_records.js";

/**
 * The single payload exit for replayed retry Jobs: a stored retry row whose
 * terminal outcome is a closed capacity protocol replays as its thrown
 * capacity error (spec: the first response and every later replay of the same
 * key MUST return the identical 422 envelope), and every other row crosses to
 * HTTP unchanged through {@link jobPayload}. Surfaces that report a replayed
 * retry Job as a request outcome MUST go through this exit; audit reads that
 * must return the complete payload regardless of outcome (the project-scoped
 * Job detail GET) use `jobPayload` directly.
 */
export function replayedJobPayload(job: JobRecord): JobPayload {
  const capacityError = replayedExportCapacityError(job) ?? replayedGenerationCapacityError(job);
  if (capacityError !== null) throw capacityError;
  return jobPayload(job);
}
