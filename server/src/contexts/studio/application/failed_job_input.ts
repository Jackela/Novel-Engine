import { dumpJson } from "./payloads.js";
import type { AddJobInput } from "./ports/job_records.js";

/**
 * The terminal fields every failure landing pins, whichever write channel
 * persists it (`addJob` for first-run rows, `markJobOutcome` for reserved
 * retries): the status is always "failed" and the event trail mirrors the
 * error message exactly.
 */
export interface FailedJobOutcome {
  readonly status: "failed";
  readonly error: string;
  readonly eventDetailsJson: string;
  readonly now: Date;
}

/** The failed outcome a retry transition records for one known miss. */
export function failedJobOutcome(error: string, now: Date): FailedJobOutcome {
  return { status: "failed", error, eventDetailsJson: dumpJson({ error }), now };
}

/**
 * The failed first-run job row: assembles the shared failed-job vocabulary
 * (status/model/requestJson/resultJson/error/eventDetailsJson) so the
 * known-error handlers pass only their per-kind provenance — provider,
 * request, and result bodies — instead of re-spelling the literals.
 */
export function failedJobInput(
  input: Omit<AddJobInput, "status" | "eventDetailsJson" | "error"> & { readonly error: string },
): AddJobInput {
  return { ...input, ...failedJobOutcome(input.error, input.now) };
}
