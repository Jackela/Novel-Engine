import type { InspectorAcceptanceUndo } from "../studioInspectorTypes";
import type { AcceptanceUndo } from "./useProposalAcceptance";

/** The live one-shot offer plus its take-once consumer. */
interface ProposalUndoSource {
  readonly undoAcceptance: AcceptanceUndo | null;
  readonly consumeAcceptanceUndo: () => AcceptanceUndo | null;
}

/**
 * DR-010: composes the inspector's one-shot acceptance undo from the live
 * offer and the caller's restore path (the same one the History tab uses).
 * Consuming before restoring makes a second activation a no-op, so one
 * acceptance can never restore twice; without a live offer this returns null
 * and the panel shows no undo affordance.
 */
export function buildProposalUndo(
  source: ProposalUndoSource,
  restore: (revisionId: string) => void | Promise<void>,
): InspectorAcceptanceUndo | null {
  if (source.undoAcceptance === null) return null;
  return {
    onUndo: async () => {
      const record = source.consumeAcceptanceUndo();
      if (record === null) return;
      await restore(record.baseRevisionId);
    },
  };
}
