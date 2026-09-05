import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useRef, useState } from "react";

import { ProposalOutcomeUnknownError, streamProposal } from "@/app/proposalStream";
import type { Project, StudioDocument, StudioJob } from "@/app/types/studio";

import { acceptProposalAndRefresh } from "./acceptProposalAndRefresh";
import { toErrorMessage } from "./toErrorMessage";
import { usePendingAction } from "./usePendingAction";
import type { ProposalAuditControl } from "./useStudioJobs";

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

interface ProposalRequest {
  readonly ownerKey: string;
  readonly requestEpoch: number;
  readonly controller: AbortController;
}

interface AcceptRequest extends ProposalRequest {
  readonly projectId: string;
}

interface UnknownProposalAttempt {
  readonly projectId: string;
  readonly operation: "continue" | "rewrite";
}

const INACTIVE_PROPOSAL_AUDIT: ProposalAuditControl = {
  status: "idle",
  audit: async () => false,
  clear: () => undefined,
  epoch: () => 0,
  isGated: () => false,
};

const PROPOSAL_KEYS = ["proposal", "accept"] as const;

type ProposalKey = (typeof PROPOSAL_KEYS)[number];

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
  const [proposalState, setProposalState] = useState<DocumentProposal | null>(null);
  const [instruction, setInstruction] = useState("");
  const { pending, begin, finish } = usePendingAction<ProposalKey>(PROPOSAL_KEYS);
  // #308: the in-flight streamed markdown lands in the proposal preview only;
  // the manuscript is touched by acceptProposal, never by the stream itself.
  const [streaming, setStreaming] = useState<StreamingProposal | null>(null);
  const [unknownAttempt, setUnknownAttempt] = useState<UnknownProposalAttempt | null>(null);
  const streamRequestRef = useRef<ProposalRequest | null>(null);
  const acceptRequestRef = useRef<AcceptRequest | null>(null);
  const requestEpochRef = useRef(0);
  const activeDocumentId = activeDocument?.id ?? null;
  const ownerKey = `${projectId}\u0000${activeDocumentId ?? ""}`;
  const ownerKeyRef = useRef(ownerKey);
  const projectIdRef = useRef<string | null>(projectId);
  const currentAuditEpoch = proposalAudit.epoch();
  const proposal =
    proposalState?.ownerKey === ownerKey && proposalState.auditEpoch === currentAuditEpoch
      ? proposalState.job
      : null;
  const streamingText =
    streaming?.ownerKey === ownerKey && streaming.auditEpoch === currentAuditEpoch
      ? streaming.text
      : null;
  const proposalOutcomeUnknown = proposalAudit.status !== "idle";
  const proposalActionsGated = proposalAudit.isGated();
  const unknownAttemptOperation =
    unknownAttempt?.projectId === projectId ? unknownAttempt.operation : "continue";

  const isCurrentRequest = useCallback(
    (requestOwnerKey: string, requestEpoch: number) =>
      ownerKeyRef.current === requestOwnerKey && requestEpochRef.current === requestEpoch,
    [],
  );

  useEffect(() => {
    ownerKeyRef.current = ownerKey;
    setProposalState((current) => (current?.ownerKey === ownerKey ? current : null));
    setStreaming((current) => (current?.ownerKey === ownerKey ? current : null));
    finish("proposal");
    finish("accept");

    return () => {
      requestEpochRef.current += 1;
      const streamRequest = streamRequestRef.current;
      if (streamRequest?.ownerKey === ownerKey) {
        streamRequest.controller.abort();
        streamRequestRef.current = null;
      }
    };
  }, [finish, ownerKey]);

  useEffect(() => {
    projectIdRef.current = projectId;
    return () => {
      if (projectIdRef.current === projectId) projectIdRef.current = null;
      const acceptRequest = acceptRequestRef.current;
      if (acceptRequest?.projectId === projectId) {
        acceptRequest.controller.abort();
        acceptRequestRef.current = null;
      }
    };
  }, [projectId]);

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

  const runProposal = useCallback(
    async (operation: "continue" | "rewrite") => {
      if (proposalAudit.isGated() || !activeDocument || !project || !begin("proposal")) return;
      const auditEpoch = proposalAudit.epoch();
      proposalAudit.clear();
      setUnknownAttempt(null);
      setProposalState(null);
      setError(null);
      const controller = new AbortController();
      const requestEpoch = requestEpochRef.current + 1;
      requestEpochRef.current = requestEpoch;
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
        if (reason instanceof ProposalOutcomeUnknownError && projectIdRef.current === projectId) {
          setProposalState(null);
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

  const retryProposalAudit = useCallback(async (): Promise<boolean> => {
    if (proposalAudit.status !== "audit_failed") return false;
    return proposalAudit.audit();
  }, [proposalAudit]);

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
    const requestEpoch = requestEpochRef.current + 1;
    requestEpochRef.current = requestEpoch;
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
        isProjectCurrent: () => projectIdRef.current === projectId && !controller.signal.aborted,
        onAcceptanceCommitted: () => {
          if (isCurrentRequest(ownerKey, requestEpoch) && !controller.signal.aborted) {
            setProposalState((current) => (current?.ownerKey === ownerKey ? null : current));
          }
        },
      });
      if (isCurrentRequest(ownerKey, requestEpoch)) {
        setProposalState((current) => (current?.ownerKey === ownerKey ? null : current));
      }
    } catch (reason) {
      if (projectIdRef.current === projectId && !controller.signal.aborted) {
        setError(toErrorMessage(reason, "Unable to accept proposal."));
      }
    } finally {
      if (acceptRequestRef.current === request) acceptRequestRef.current = null;
      if (isCurrentRequest(ownerKey, requestEpoch)) finish("accept");
    }
  }, [
    activeDocument,
    begin,
    finish,
    loadJobs,
    captureAcceptedDocument,
    ownerKey,
    projectId,
    proposal,
    proposalAudit,
    isCurrentRequest,
    setError,
    setProject,
  ]);

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
