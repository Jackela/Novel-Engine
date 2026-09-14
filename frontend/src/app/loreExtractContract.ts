import { parseJob } from "@/app/apiWorkflowContract";
import type { StudioJob } from "@/app/types/studio";

/**
 * Runtime-validate the lorebook wizard's extraction response (#614) at the
 * API boundary: the payload must be a terminal `lore-extract` job whose
 * candidate set is present — the synchronous execution model answers 200
 * with a completed or failed job, so the wizard branches on `status` itself.
 * Candidates are suggestions only, never persisted content.
 */
export function parseLoreExtractJob(value: unknown): StudioJob {
  const job = parseJob(value, "lore extraction job");
  if (job.kind !== "lore-extract") {
    throw new Error("Invalid lore extraction job.kind");
  }
  if (job.status !== "completed" && job.status !== "failed") {
    throw new Error("Invalid lore extraction job.status");
  }
  if (job.result.candidates === undefined) {
    throw new Error("Invalid lore extraction job.result.candidates");
  }
  return job;
}
