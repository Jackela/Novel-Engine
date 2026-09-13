import { dumpJson } from "./payloads.js";
import type { AddJobInput } from "./ports/job_records.js";

/**
 * The terminal fields every failure landing pins, whichever write channel
 * persists it (`addJob` for first-run rows, `markJobOutcome` for reserved
 * retries): the status is always "failed" and the event trail mirrors the
 * error message exactly. When the executor resolved honest model provenance
 * before failing, the overload pins it as a required field; otherwise the
 * field stays absent so the spread never clobbers a caller-supplied model.
 */
interface FailedJobOutcome {
  readonly status: "failed";
  readonly error: string;
  readonly eventDetailsJson: string;
  readonly now: Date;
}

/** The failed outcome of a retry whose executor already resolved the model. */
interface FailedModelJobOutcome extends FailedJobOutcome {
  readonly model: string;
}

/** The failed outcome a retry transition records for one known miss. */
export function failedJobOutcome(error: string, now: Date): FailedJobOutcome;
export function failedJobOutcome(error: string, now: Date, model: string): FailedModelJobOutcome;
export function failedJobOutcome(
  error: string,
  now: Date,
  model?: string | undefined,
): FailedJobOutcome {
  return {
    status: "failed",
    ...(model === undefined ? {} : { model }),
    error,
    eventDetailsJson: dumpJson({ error }),
    now,
  };
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
