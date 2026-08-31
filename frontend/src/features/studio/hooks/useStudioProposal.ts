import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useRef, useState } from "react";

import { streamProposal } from "@/app/proposalStream";
import type { Project, StudioDocument, StudioJob } from "@/app/types/studio";

import { acceptProposalAndRefresh } from "./acceptProposalAndRefresh";
import { toErrorMessage } from "./toErrorMessage";
import { usePendingAction } from "./usePendingAction";

interface DocumentProposal {
  readonly ownerKey: string;
  readonly job: StudioJob;
}

interface StreamingProposal {
  readonly ownerKey: string;
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
) {
  const [proposalState, setProposalState] = useState<DocumentProposal | null>(null);
  const [instruction, setInstruction] = useState("");
  const { pending, begin, finish } = usePendingAction<ProposalKey>(PROPOSAL_KEYS);
  // #308: the in-flight streamed markdown lands in the proposal preview only;
  // the manuscript is touched by acceptProposal, never by the stream itself.
  const [streaming, setStreaming] = useState<StreamingProposal | null>(null);
  const streamRequestRef = useRef<ProposalRequest | null>(null);
  const acceptRequestRef = useRef<AcceptRequest | null>(null);
  const requestEpochRef = useRef(0);
  const activeDocumentId = activeDocument?.id ?? null;
  const ownerKey = `${projectId}\u0000${activeDocumentId ?? ""}`;
  const ownerKeyRef = useRef(ownerKey);
  const projectIdRef = useRef<string | null>(projectId);
  const proposal = proposalState?.ownerKey === ownerKey ? proposalState.job : null;
  const streamingText = streaming?.ownerKey === ownerKey ? streaming.text : null;

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
        const currentProposal = current?.ownerKey === ownerKey ? current.job : null;
        const next =
          typeof nextProposal === "function" ? nextProposal(currentProposal) : nextProposal;
        return next && activeDocumentId ? { ownerKey, job: next } : null;
      });
    },
    [activeDocumentId, ownerKey],
  );

  const runProposal = useCallback(
    async (operation: "continue" | "rewrite") => {
      if (!activeDocument || !project || !begin("proposal")) return;
      setError(null);
      const controller = new AbortController();
      const requestEpoch = requestEpochRef.current + 1;
      requestEpochRef.current = requestEpoch;
      const request = { ownerKey, requestEpoch, controller };
      streamRequestRef.current = request;
      setStreaming({ ownerKey, requestEpoch, text: "" });
      try {
        const nextProposal = await streamProposal({
          projectId,
          documentId: activeDocument.id,
          operation,
          instruction,
          provider: String(project.settings.provider ?? "mock"),
          signal: controller.signal,
          onDelta: (text) => {
            if (!isCurrentRequest(ownerKey, requestEpoch) || controller.signal.aborted) return;
            setStreaming((current) =>
              current?.ownerKey === ownerKey && current.requestEpoch === requestEpoch
                ? { ...current, text: current.text + text }
                : current,
            );
          },
        });
        if (!isCurrentRequest(ownerKey, requestEpoch) || controller.signal.aborted) return;
        setProposalState({ ownerKey, job: nextProposal });
      } catch (reason) {
        if (isCurrentRequest(ownerKey, requestEpoch) && !controller.signal.aborted) {
          setError(toErrorMessage(reason, "Unable to create proposal."));
        }
      } finally {
        if (streamRequestRef.current === request) streamRequestRef.current = null;
        if (isCurrentRequest(ownerKey, requestEpoch)) {
          setStreaming((current) =>
            current?.ownerKey === ownerKey && current.requestEpoch === requestEpoch
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
      setError,
    ],
  );

  const stopProposal = useCallback(() => {
    streamRequestRef.current?.controller.abort();
  }, []);

  const acceptProposal = useCallback(async () => {
    if (!proposal || !activeDocument || acceptRequestRef.current || !begin("accept")) return;
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
  };
}
