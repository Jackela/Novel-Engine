import type { Dispatch, SetStateAction } from "react";
import { useCallback, useRef, useState } from "react";

import { ProposalOutcomeUnknownError, streamProposal } from "@/app/proposalStream";
import type { Project, StudioDocument, StudioJob } from "@/app/types/studio";

import { toErrorMessage } from "./toErrorMessage";
import type { PendingActionController } from "./usePendingAction";
import type { ProposalAuditControl } from "./useStudioJobs";

export const PROPOSAL_KEYS = ["proposal", "accept"] as const;

export type ProposalKey = (typeof PROPOSAL_KEYS)[number];

interface DocumentProposal {
  readonly ownerKey: string;
  readonly auditEpoch: number;
  readonly job: StudioJob;
}

interface StreamingProposal {
  readonly ownerKey: string;
  readonly auditEpoch: number;
  readonly requestEpoch: number;
  readonly text: string;
}

export interface ProposalRequest {
  readonly ownerKey: string;
  readonly requestEpoch: number;
  readonly controller: AbortController;
}

interface UnknownProposalAttempt {
  readonly projectId: string;
  readonly operation: "continue" | "rewrite";
}

export interface ProposalStreamSessionOptions {
  readonly projectId: string;
  readonly activeDocument: StudioDocument | null;
  readonly project: Project | null;
  /** Binds proposal state to one (project, document) owner pair. */
  readonly ownerKey: string;
  readonly activeDocumentId: string | null;
  readonly currentAuditEpoch: number;
  readonly proposalAudit: ProposalAuditControl;
  readonly setError: Dispatch<SetStateAction<string | null>>;
  readonly pending: Pick<PendingActionController<ProposalKey>, "begin" | "finish">;
  readonly isCurrentRequest: (requestOwnerKey: string, requestEpoch: number) => boolean;
  /** Claims the next ledger epoch; any concurrent accept is invalidated. */
  readonly nextRequestEpoch: () => number;
  /** Reads the facade-owned project currency ref at call time. */
  readonly isProjectLive: (candidateProjectId: string) => boolean;
}

/**
 * One proposal generation session for the active document: the in-flight
 * streamed preview, the landed proposal job, and the unknown-outcome attempt
 * left behind when a terminal frame is lost. All state is owner- and
 * audit-epoch-gated so stale sessions never surface.
 */
export function useProposalStreamSession({
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
}: ProposalStreamSessionOptions) {
  const [proposalState, setProposalState] = useState<DocumentProposal | null>(null);
  const [instruction, setInstruction] = useState("");
  // #308: the in-flight streamed markdown lands in the proposal preview only;
  // the manuscript is touched by acceptProposal, never by the stream itself.
  const [streaming, setStreaming] = useState<StreamingProposal | null>(null);
  const [unknownAttempt, setUnknownAttempt] = useState<UnknownProposalAttempt | null>(null);
  const streamRequestRef = useRef<ProposalRequest | null>(null);
  const proposal =
    proposalState?.ownerKey === ownerKey && proposalState.auditEpoch === currentAuditEpoch
      ? proposalState.job
      : null;
  const streamingText =
    streaming?.ownerKey === ownerKey && streaming.auditEpoch === currentAuditEpoch
      ? streaming.text
      : null;
  const unknownAttemptOperation =
    unknownAttempt?.projectId === projectId ? unknownAttempt.operation : "continue";

  const setProposal = useCallback<Dispatch<SetStateAction<StudioJob | null>>>(
    (nextProposal) => {
      setProposalState((current) => {
        const currentProposal =
          current?.ownerKey === ownerKey && current.auditEpoch === currentAuditEpoch
            ? current.job
            : null;
        const next =
          typeof nextProposal === "function" ? nextProposal(currentProposal) : nextProposal;
        return next && activeDocumentId
          ? { ownerKey, auditEpoch: currentAuditEpoch, job: next }
          : null;
      });
    },
    [activeDocumentId, currentAuditEpoch, ownerKey],
  );

  /** Drops proposal/streaming state that does not belong to the new owner. */
  const reconcileOwnerState = useCallback((nextOwnerKey: string) => {
    setProposalState((current) => (current?.ownerKey === nextOwnerKey ? current : null));
    setStreaming((current) => (current?.ownerKey === nextOwnerKey ? current : null));
  }, []);

  /** Aborts the stream request still attached to the departed owner. */
  const detachStream = useCallback((previousOwnerKey: string) => {
    const streamRequest = streamRequestRef.current;
    if (streamRequest?.ownerKey === previousOwnerKey) {
      streamRequest.controller.abort();
      streamRequestRef.current = null;
    }
  }, []);

  const clearCurrentProposal = useCallback(() => {
    setProposalState((current) => (current?.ownerKey === ownerKey ? null : current));
  }, [ownerKey]);

  const runProposal = useCallback(
    async (operation: "continue" | "rewrite") => {
      if (proposalAudit.isGated() || !activeDocument || !project || !begin("proposal")) return;
      const auditEpoch = proposalAudit.epoch();
      proposalAudit.clear();
      setUnknownAttempt(null);
      setProposalState(null);
      setError(null);
      const controller = new AbortController();
      const requestEpoch = nextRequestEpoch();
      const request = { ownerKey, requestEpoch, controller };
      streamRequestRef.current = request;
      setStreaming({ ownerKey, auditEpoch, requestEpoch, text: "" });
      try {
        const nextProposal = await streamProposal({
          projectId,
          documentId: activeDocument.id,
          operation,
          instruction,
          provider: String(project.settings.provider ?? "mock"),
          signal: controller.signal,
          onDelta: (text) => {
            if (
              proposalAudit.epoch() !== auditEpoch ||
              !isCurrentRequest(ownerKey, requestEpoch) ||
              controller.signal.aborted
            ) {
              return;
            }
            setStreaming((current) =>
              current?.ownerKey === ownerKey &&
              current.auditEpoch === auditEpoch &&
              current.requestEpoch === requestEpoch
                ? { ...current, text: current.text + text }
                : current,
            );
          },
        });
        if (
          proposalAudit.epoch() !== auditEpoch ||
          !isCurrentRequest(ownerKey, requestEpoch) ||
          controller.signal.aborted
        ) {
          return;
        }
        setProposalState({ ownerKey, auditEpoch, job: nextProposal });
      } catch (reason) {
        if (reason instanceof ProposalOutcomeUnknownError && isProjectLive(projectId)) {
          // Ownership stays inside the state update: a stale session must not
          // drop a landed proposal that a newer request already owns.
          setProposalState((current) =>
            current?.ownerKey === ownerKey && current.auditEpoch === auditEpoch ? null : current,
          );
          setStreaming((current) =>
            current?.ownerKey === ownerKey &&
            current.auditEpoch === auditEpoch &&
            current.requestEpoch === requestEpoch
              ? null
              : current,
          );
          setUnknownAttempt({ projectId, operation });
          if (streamRequestRef.current === request) streamRequestRef.current = null;
          finish("proposal");
          await proposalAudit.audit();
        } else if (proposalAudit.epoch() !== auditEpoch) {
          return;
        } else if (isCurrentRequest(ownerKey, requestEpoch) && !controller.signal.aborted) {
          setError(toErrorMessage(reason, "Unable to create proposal."));
        }
      } finally {
        if (streamRequestRef.current === request) streamRequestRef.current = null;
        if (isCurrentRequest(ownerKey, requestEpoch)) {
          setStreaming((current) =>
            current?.ownerKey === ownerKey &&
            current.auditEpoch === auditEpoch &&
            current.requestEpoch === requestEpoch
              ? null
              : current,
          );
          finish("proposal");
        }
      }
    },
    [
      activeDocument,
      begin,
      finish,
      instruction,
      isCurrentRequest,
      isProjectLive,
      nextRequestEpoch,
      ownerKey,
      project,
      projectId,
      proposalAudit,
      setError,
    ],
  );

  const stopProposal = useCallback(() => {
    streamRequestRef.current?.controller.abort();
  }, []);

  return {
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
  };
}
