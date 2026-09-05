import { dumpJson } from "./payloads.js";
import type { MarkJobOutcomeInput } from "./ports/studio_store.js";

export const PROPOSAL_RETRY_STALE_BASE_ERROR = "Proposal retry base revision is no longer current.";

/** The exact failed outcome for a retry whose immutable base is no longer current. */
export function proposalRetryStaleBaseOutcome(
  baseRevisionId: string,
  currentRevisionId: string,
  now: Date,
): MarkJobOutcomeInput {
  return {
    status: "failed",
    resultJson: dumpJson({
      proposal_markdown: "",
      base_revision_id: baseRevisionId,
      accepted_revision_id: null,
    }),
    error: PROPOSAL_RETRY_STALE_BASE_ERROR,
    eventDetailsJson: dumpJson({
      error: PROPOSAL_RETRY_STALE_BASE_ERROR,
      reason: "base_revision_changed",
      base_revision_id: baseRevisionId,
      current_revision_id: currentRevisionId,
    }),
    now,
  };
}
