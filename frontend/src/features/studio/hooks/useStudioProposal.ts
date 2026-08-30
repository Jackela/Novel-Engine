import type { Dispatch, SetStateAction } from "react";
import { useCallback, useRef, useState } from "react";

import { streamProposal } from "@/app/proposalStream";
import type { Project, StudioDocument, StudioJob } from "@/app/types/studio";
import type { InspectorTab } from "@/features/studio/studioConstants";

import { acceptProposalAndRefresh } from "./acceptProposalAndRefresh";
import { toErrorMessage } from "./toErrorMessage";
import { usePendingAction } from "./usePendingAction";

interface DocumentProposal {
  readonly documentId: string;
  readonly job: StudioJob;
}

const PROPOSAL_KEYS = ["proposal", "accept"] as const;

type ProposalKey = (typeof PROPOSAL_KEYS)[number];

export function useStudioProposal(
  projectId: string,
  activeDocument: StudioDocument | null,
  project: Project | null,
  setProject: Dispatch<SetStateAction<Project | null>>,
  setInspector: Dispatch<SetStateAction<InspectorTab>>,
  setError: Dispatch<SetStateAction<string | null>>,
  loadJobs: () => void,
  onAccepted: (document: StudioDocument) => void,
) {
  const [proposalState, setProposalState] = useState<DocumentProposal | null>(null);
  const [instruction, setInstruction] = useState("");
  const { pending, begin, finish } = usePendingAction<ProposalKey>(PROPOSAL_KEYS);
  // #308: the in-flight streamed markdown lands in the proposal preview only;
  // the manuscript is touched by acceptProposal, never by the stream itself.
  const [streaming, setStreaming] = useState<{
    documentId: string;
    text: string;
  } | null>(null);
  const streamController = useRef<AbortController | null>(null);
  const activeDocumentId = activeDocument?.id ?? null;
  const proposal = proposalState?.documentId === activeDocumentId ? proposalState.job : null;
  const streamingText = streaming?.documentId === activeDocumentId ? streaming.text : null;

  const setProposal = useCallback<Dispatch<SetStateAction<StudioJob | null>>>(
    (nextProposal) => {
      setProposalState((current) => {
        const currentProposal = current?.documentId === activeDocumentId ? current.job : null;
        const next =
          typeof nextProposal === "function" ? nextProposal(currentProposal) : nextProposal;
        return next && activeDocumentId ? { documentId: activeDocumentId, job: next } : null;
      });
    },
    [activeDocumentId],
  );

  const runProposal = useCallback(
    async (operation: "continue" | "rewrite") => {
      if (!activeDocument || !project || !begin("proposal")) return;
      setError(null);
      const controller = new AbortController();
      streamController.current = controller;
      setStreaming({ documentId: activeDocument.id, text: "" });
      try {
        const nextProposal = await streamProposal({
          projectId,
          documentId: activeDocument.id,
          operation,
          instruction,
          provider: String(project.settings.provider ?? "mock"),
          signal: controller.signal,
          onDelta: (text) =>
            setStreaming((current) =>
              current === null
                ? current
                : { documentId: current.documentId, text: current.text + text },
            ),
        });
        setProposalState({ documentId: activeDocument.id, job: nextProposal });
        setInspector("copilot");
      } catch (reason) {
        if (!controller.signal.aborted) {
          setError(toErrorMessage(reason, "Unable to create proposal."));
        }
      } finally {
        streamController.current = null;
        setStreaming(null);
        finish("proposal");
      }
    },
    [activeDocument, begin, finish, project, projectId, instruction, setError, setInspector],
  );

  const stopProposal = useCallback(() => {
    streamController.current?.abort();
  }, []);

  const acceptProposal = useCallback(async () => {
    if (!proposal || !activeDocument || !begin("accept")) return;
    setError(null);
    try {
      await acceptProposalAndRefresh({
        projectId,
        proposalId: proposal.id,
        documentId: activeDocument.id,
        setProject,
        onAccepted,
        loadJobs,
      });
      setProposalState(null);
    } catch (reason) {
      setError(toErrorMessage(reason, "Unable to accept proposal."));
    } finally {
      finish("accept");
    }
  }, [
    activeDocument,
    begin,
    finish,
    loadJobs,
    onAccepted,
    projectId,
    proposal,
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
