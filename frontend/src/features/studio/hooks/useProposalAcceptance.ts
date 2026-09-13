import type { Dispatch, SetStateAction } from "react";
import { useCallback, useRef } from "react";

import type { Project, StudioDocument, StudioJob } from "@/app/types/studio";

import { acceptProposalAndRefresh } from "./acceptProposalAndRefresh";
import { toErrorMessage } from "./toErrorMessage";
import type { PendingActionController } from "./usePendingAction";
import type { ProposalKey, ProposalRequest } from "./useProposalStreamSession";
import type { ProposalAuditControl } from "./useStudioJobs";

interface AcceptRequest extends ProposalRequest {
  readonly projectId: string;
}

interface ProposalAcceptanceOptions {
  readonly projectId: string;
  readonly activeDocument: StudioDocument | null;
  readonly ownerKey: string;
  readonly proposal: StudioJob | null;
  readonly proposalAudit: ProposalAuditControl;
  readonly setError: Dispatch<SetStateAction<string | null>>;
  readonly setProject: Dispatch<SetStateAction<Project | null>>;
  readonly loadJobs: () => void;
  readonly captureAcceptedDocument: (
    documentId: string,
  ) => ((document: StudioDocument) => void) | undefined;
  readonly pending: Pick<PendingActionController<ProposalKey>, "begin" | "finish">;
  readonly isCurrentRequest: (requestOwnerKey: string, requestEpoch: number) => boolean;
  /** Claims the next ledger epoch; any in-flight stream is invalidated. */
  readonly nextRequestEpoch: () => number;
  /** Reads the facade-owned project currency ref at call time. */
  readonly isProjectLive: (candidateProjectId: string) => boolean;
  readonly clearCurrentProposal: () => void;
}

/**
 * Landing coordination for an accepted proposal: deduplicates concurrent
 * accepts, keeps project currency ref scoped so a committed acceptance and its
 * refresh are dropped when the project owner changes, and clears the landed
 * proposal exactly once per committed accept.
 */
export function useProposalAcceptance({
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
}: ProposalAcceptanceOptions) {
  const acceptRequestRef = useRef<AcceptRequest | null>(null);

  /** Aborts the accept request still attached to the departed project. */
  const detachAccept = useCallback((previousProjectId: string) => {
    const acceptRequest = acceptRequestRef.current;
    if (acceptRequest?.projectId === previousProjectId) {
      acceptRequest.controller.abort();
      acceptRequestRef.current = null;
    }
  }, []);

  const acceptProposal = useCallback(async () => {
    if (
      proposalAudit.isGated() ||
      !proposal ||
      !activeDocument ||
      acceptRequestRef.current ||
      !begin("accept")
    ) {
      return;
    }
    const onAccepted = captureAcceptedDocument(activeDocument.id);
    setError(null);
    const requestEpoch = nextRequestEpoch();
    const controller = new AbortController();
    const request = { projectId, ownerKey, requestEpoch, controller };
    acceptRequestRef.current = request;
    try {
      await acceptProposalAndRefresh({
        projectId,
        proposalId: proposal.id,
        documentId: activeDocument.id,
        setProject,
        onAccepted,
        loadJobs,
        signal: controller.signal,
        isProjectCurrent: () => isProjectLive(projectId) && !controller.signal.aborted,
        onAcceptanceCommitted: () => {
          if (isCurrentRequest(ownerKey, requestEpoch) && !controller.signal.aborted) {
            clearCurrentProposal();
          }
        },
      });
      if (isCurrentRequest(ownerKey, requestEpoch)) {
        clearCurrentProposal();
      }
    } catch (reason) {
      if (isProjectLive(projectId) && !controller.signal.aborted) {
        setError(toErrorMessage(reason, "Unable to accept proposal."));
      }
    } finally {
      if (acceptRequestRef.current === request) acceptRequestRef.current = null;
      if (isCurrentRequest(ownerKey, requestEpoch)) finish("accept");
    }
  }, [
    activeDocument,
    begin,
    clearCurrentProposal,
    finish,
    isCurrentRequest,
    isProjectLive,
    loadJobs,
    captureAcceptedDocument,
    nextRequestEpoch,
    ownerKey,
    projectId,
    proposal,
    proposalAudit,
    setError,
    setProject,
  ]);

  return { acceptProposal, detachAccept };
}
