import { ApiContractError } from "@/app/apiContract";
import { parseJob } from "@/app/apiWorkflowContract";
import type { StudioJob } from "@/app/types/studio";

/**
 * Runtime-validate the lorebook wizard's extraction response (#614) at the
 * API boundary: the payload must be a terminal `lore-extract` job whose
 * candidate set is present — the synchronous execution model answers 200
 * with a completed or failed job, so the wizard branches on `status` itself.
 * Candidates are suggestions only, never persisted content. Failures throw
 * `ApiContractError` so the localized surface can name the refused shape
 * (DR-021) instead of echoing the raw label.
 */
export function parseLoreExtractJob(value: unknown): StudioJob {
  const job = parseJob(value, "lore extraction job");
  if (job.kind !== "lore-extract") {
    throw new ApiContractError("lore extraction job.kind");
  }
  if (job.status !== "completed" && job.status !== "failed") {
    throw new ApiContractError("lore extraction job.status");
  }
  if (job.result.candidates === undefined) {
    throw new ApiContractError("lore extraction job.result.candidates");
  }
  return job;
}
