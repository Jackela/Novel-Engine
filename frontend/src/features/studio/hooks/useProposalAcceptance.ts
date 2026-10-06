import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { translateActive } from "@/app/i18n/translate";
import type { Project, StudioDocument, StudioJob } from "@/app/types/studio";
import { acceptProposalAndRefresh } from "./acceptProposalAndRefresh";
import { toErrorMessage } from "./toErrorMessage";
import type { PendingActionController } from "./usePendingAction";
import type { ProposalKey, ProposalRequest } from "./useProposalStreamSession";
import type { ProposalAuditControl } from "./useStudioJobs";

interface AcceptRequest extends ProposalRequest {
  readonly projectId: string;
}

/** DR-010: the pre-accept revision of one committed acceptance. */
export interface AcceptanceUndo {
  readonly documentId: string;
  readonly baseRevisionId: string;
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
  // null: no live offer (never accepted, taken, or cleared); a record: a live
  // one-shot offer for the document that accepted (DR-010).
  const [acceptanceUndoState, setAcceptanceUndoState] = useState<AcceptanceUndo | null>(null);
  const acceptanceUndoRef = useRef<AcceptanceUndo | null>(null);
  const activeDocumentIdRef = useRef<string | null>(activeDocument?.id ?? null);
  useEffect(() => {
    // Latest-value ref for the take-once guard; synced after commit so no
    // render work mutates it (React may replay discarded renders).
    activeDocumentIdRef.current = activeDocument?.id ?? null;
  }, [activeDocument?.id]);

  /** Aborts the accept request still attached to the departed project. */
  const detachAccept = useCallback((previousProjectId: string) => {
    const acceptRequest = acceptRequestRef.current;
    if (acceptRequest?.projectId === previousProjectId) {
      acceptRequest.controller.abort();
      acceptRequestRef.current = null;
    }
  }, []);

  /** DR-010: the one-shot undo offer, visible only for the document that accepted. */
  const undoAcceptance =
    acceptanceUndoState !== null && acceptanceUndoState.documentId === (activeDocument?.id ?? null)
      ? acceptanceUndoState
      : null;

  /** Takes the offer so a second invocation can never restore twice. */
  const consumeAcceptanceUndo = useCallback((): AcceptanceUndo | null => {
    const record = acceptanceUndoRef.current;
    if (record === null || record.documentId !== activeDocumentIdRef.current) return null;
    acceptanceUndoRef.current = null;
    setAcceptanceUndoState(null);
    return record;
  }, []);

  /** Drops the offer on an owner change; the revision stays in History. */
  const clearAcceptanceUndo = useCallback(() => {
    acceptanceUndoRef.current = null;
    setAcceptanceUndoState(null);
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
    // DR-010: the accepted revision is written on top of this base revision;
    // it is the one-shot undo target, and absence simply offers no undo.
    const baseRevisionId = proposal.result.base_revision_id;
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
            if (baseRevisionId !== undefined) {
              const undo = { documentId: activeDocument.id, baseRevisionId };
              acceptanceUndoRef.current = undo;
              setAcceptanceUndoState(undo);
            }
          }
        },
      });
      if (isCurrentRequest(ownerKey, requestEpoch)) {
        clearCurrentProposal();
      }
    } catch (reason) {
      if (isProjectLive(projectId) && !controller.signal.aborted) {
        setError(toErrorMessage(reason, translateActive("errors.acceptProposal")));
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

  return {
    acceptProposal,
    detachAccept,
    undoAcceptance,
    consumeAcceptanceUndo,
    clearAcceptanceUndo,
  };
}
