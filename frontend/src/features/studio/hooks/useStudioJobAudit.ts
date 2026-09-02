import type { Dispatch, SetStateAction } from "react";
import { useMemo } from "react";

import type { ProposalAuditControl } from "./useStudioJobs";
import { useStudioJobs } from "./useStudioJobs";

/** Bind the jobs reader and its project-owned unknown-outcome audit contract. */
export function useStudioJobAudit(
  projectId: string,
  setError: Dispatch<SetStateAction<string | null>>,
) {
  const jobs = useStudioJobs(projectId, setError);
  const proposalAudit = useMemo<ProposalAuditControl>(
    () => ({
      status: jobs.proposalAuditStatus,
      audit: jobs.auditProposalOutcome,
      clear: jobs.clearProposalAudit,
      epoch: jobs.proposalAuditEpoch,
      isGated: jobs.isProposalAuditGated,
    }),
    [
      jobs.auditProposalOutcome,
      jobs.clearProposalAudit,
      jobs.isProposalAuditGated,
      jobs.proposalAuditEpoch,
      jobs.proposalAuditStatus,
    ],
  );
  return { ...jobs, proposalAudit, proposalAuditGated: proposalAudit.isGated() };
}
