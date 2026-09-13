import type { Dispatch, SetStateAction } from "react";
import { useCallback } from "react";

import type { Project, StudioDocument } from "@/app/types/studio";
import type { ProposalAuditControl } from "./useStudioJobs";
import { useWholeBookChapterRun } from "./useWholeBookChapterRun";
import { useWholeBookRunLedger } from "./useWholeBookRunLedger";

export type { WholeBookPhase } from "./useWholeBookRunLedger";

const INACTIVE_PROPOSAL_AUDIT: ProposalAuditControl = {
  status: "idle",
  audit: async () => false,
  clear: () => undefined,
  epoch: () => 0,
  isGated: () => false,
};

interface UseWholeBookLoopArgs {
  readonly projectId: string;
  readonly provider: string;
  readonly setProject: Dispatch<SetStateAction<Project | null>>;
  readonly loadJobs: () => void;
  readonly proposalAudit?: ProposalAuditControl;
  /** Captures the draft version an acceptance may replace before its request starts. */
  readonly captureAcceptedDocument?: (
    documentId: string,
  ) => ((document: StudioDocument) => void) | undefined;
}

/**
 * Facade for the whole-book loop (#318): composes the run ledger (owner
 * project, run epoch, active run, published phase, stop) with the per-chapter
 * run executor behind the pre-split return shape, and owns the shared
 * jobs-audit gate surface both consumers observe.
 */
export function useWholeBookLoop({
  projectId,
  provider,
  setProject,
  loadJobs,
  proposalAudit = INACTIVE_PROPOSAL_AUDIT,
  captureAcceptedDocument,
}: UseWholeBookLoopArgs) {
  const ledger = useWholeBookRunLedger({ projectId });
  const { start } = useWholeBookChapterRun({
    projectId,
    provider,
    setProject,
    loadJobs,
    proposalAudit,
    captureAcceptedDocument,
    ledger,
  });

  const proposalOutcomeUnknown = proposalAudit.status !== "idle";
  const proposalActionsGated = proposalAudit.isGated();

  const retryProposalAudit = useCallback(async (): Promise<boolean> => {
    if (proposalAudit.status !== "audit_failed") return false;
    return proposalAudit.audit();
  }, [proposalAudit]);

  return {
    phase: ledger.phase,
    start,
    stop: ledger.stop,
    proposalOutcomeUnknown,
    proposalAuditStatus: proposalAudit.status,
    proposalActionsGated,
    retryProposalAudit,
  };
}
