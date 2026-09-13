import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useRef } from "react";

import type { Project, StudioDocument } from "@/app/types/studio";

import { usePendingAction } from "./usePendingAction";
import { useProposalAcceptance } from "./useProposalAcceptance";
import { PROPOSAL_KEYS, useProposalStreamSession } from "./useProposalStreamSession";
import type { ProposalAuditControl } from "./useStudioJobs";

const INACTIVE_PROPOSAL_AUDIT: ProposalAuditControl = {
  status: "idle",
  audit: async () => false,
  clear: () => undefined,
  epoch: () => 0,
  isGated: () => false,
};

/**
 * Facade for the proposal workspace: composes the stream session (generation
 * and landed job) with the acceptance landing flow behind the pre-split
 * return shape, and owns the shared request ledger plus owner-key
 * reconciliation both sub-hooks coordinate through.
 */
export function useStudioProposal(
  projectId: string,
  activeDocument: StudioDocument | null,
  project: Project | null,
  setProject: Dispatch<SetStateAction<Project | null>>,
  setError: Dispatch<SetStateAction<string | null>>,
  loadJobs: () => void,
  captureAcceptedDocument: (documentId: string) => ((document: StudioDocument) => void) | undefined,
  proposalAudit: ProposalAuditControl = INACTIVE_PROPOSAL_AUDIT,
) {
  const { pending, begin, finish } = usePendingAction(PROPOSAL_KEYS);
  const activeDocumentId = activeDocument?.id ?? null;
  const ownerKey = `${projectId}\u0000${activeDocumentId ?? ""}`;
  const ownerKeyRef = useRef(ownerKey);
  const projectIdRef = useRef<string | null>(projectId);
  const requestEpochRef = useRef(0);
  const currentAuditEpoch = proposalAudit.epoch();

  const isCurrentRequest = useCallback(
    (requestOwnerKey: string, requestEpoch: number) =>
      ownerKeyRef.current === requestOwnerKey && requestEpochRef.current === requestEpoch,
    [],
  );

  const nextRequestEpoch = useCallback(() => {
    const requestEpoch = requestEpochRef.current + 1;
    requestEpochRef.current = requestEpoch;
    return requestEpoch;
  }, []);

  const isProjectLive = useCallback(
    (candidateProjectId: string) => projectIdRef.current === candidateProjectId,
    [],
  );

  const {
    proposal,
    setProposal,
    clearCurrentProposal,
    instruction,
    setInstruction,
    runProposal,
    stopProposal,
    streamingText,
    unknownAttemptOperation,
    reconcileOwnerState,
    detachStream,
  } = useProposalStreamSession({
    projectId,
    activeDocument,
    project,
    ownerKey,
    activeDocumentId,
    currentAuditEpoch,
    proposalAudit,
    setError,
    pending: { begin, finish },
    isCurrentRequest,
    nextRequestEpoch,
    isProjectLive,
  });

  const { acceptProposal, detachAccept } = useProposalAcceptance({
    projectId,
    activeDocument,
    ownerKey,
    proposal,
    proposalAudit,
    setError,
    setProject,
    loadJobs,
    captureAcceptedDocument,
    pending: { begin, finish },
    isCurrentRequest,
    nextRequestEpoch,
    isProjectLive,
    clearCurrentProposal,
  });

  useEffect(() => {
    ownerKeyRef.current = ownerKey;
    reconcileOwnerState(ownerKey);
    finish("proposal");
    finish("accept");

    return () => {
      requestEpochRef.current += 1;
      detachStream(ownerKey);
    };
  }, [detachStream, finish, ownerKey, reconcileOwnerState]);

  useEffect(() => {
    projectIdRef.current = projectId;
    return () => {
      if (projectIdRef.current === projectId) projectIdRef.current = null;
      detachAccept(projectId);
    };
  }, [detachAccept, projectId]);

  const proposalOutcomeUnknown = proposalAudit.status !== "idle";
  const proposalActionsGated = proposalAudit.isGated();

  const retryProposalAudit = useCallback(async (): Promise<boolean> => {
    if (proposalAudit.status !== "audit_failed") return false;
    return proposalAudit.audit();
  }, [proposalAudit]);

  return {
    proposal,
    setProposal,
    instruction,
    setInstruction,
    runProposal,
    stopProposal,
    streamingText,
    acceptProposal,
    pending,
    isRunningProposal: pending.proposal,
    isAcceptingProposal: pending.accept,
    proposalOutcomeUnknown,
    proposalAuditStatus: proposalAudit.status,
    proposalActionsGated,
    unknownAttemptOperation,
    retryProposalAudit,
  };
}
