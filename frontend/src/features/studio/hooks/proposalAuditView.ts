import type { ProposalAuditStatus } from "./useStudioJobs";

/** Adapt one shared audit state to either proposal control surface. */
export function buildProposalAuditView(
  proposalOutcomeUnknown: boolean,
  proposalAuditStatus: ProposalAuditStatus,
  retry: () => Promise<boolean>,
) {
  return {
    proposalOutcomeUnknown,
    proposalAuditStatus,
    onRetryProposalAudit: async (): Promise<void> => {
      await retry();
    },
  };
}
