import { useCallback, useRef, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';

import { api } from '@/app/api';
import type { InspectorTab } from '@/features/studio/studioConstants';
import type { Project, StudioDocument, StudioJob } from '@/app/types/studio';

interface DocumentProposal {
  readonly documentId: string;
  readonly job: StudioJob;
}

interface PendingProposalActions {
  readonly proposal: boolean;
  readonly accept: boolean;
}

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
  const [instruction, setInstruction] = useState('');
  const [pending, setPending] = useState<PendingProposalActions>({
    proposal: false,
    accept: false,
  });
  const pendingRef = useRef<Set<keyof PendingProposalActions> | null>(null);
  const activeDocumentId = activeDocument?.id ?? null;
  const proposal = proposalState?.documentId === activeDocumentId ? proposalState.job : null;

  const begin = useCallback((key: keyof PendingProposalActions) => {
    const current =
      pendingRef.current ?? (pendingRef.current = new Set<keyof PendingProposalActions>());
    if (current.has(key)) return false;
    current.add(key);
    setPending((current) => ({ ...current, [key]: true }));
    return true;
  }, []);

  const finish = useCallback((key: keyof PendingProposalActions) => {
    pendingRef.current?.delete(key);
    setPending((current) => ({ ...current, [key]: false }));
  }, []);

  const setProposal = useCallback<Dispatch<SetStateAction<StudioJob | null>>>(
    (nextProposal) => {
      setProposalState((current) => {
        const currentProposal = current?.documentId === activeDocumentId ? current.job : null;
        const next =
          typeof nextProposal === 'function' ? nextProposal(currentProposal) : nextProposal;
        return next && activeDocumentId ? { documentId: activeDocumentId, job: next } : null;
      });
    },
    [activeDocumentId],
  );

  const runProposal = useCallback(
    async (operation: 'continue' | 'rewrite') => {
      if (!activeDocument || !project || !begin('proposal')) return;
      setError(null);
      try {
        const nextProposal = await api.proposal(
          projectId,
          activeDocument.id,
          operation,
          instruction,
          String(project.settings.provider ?? 'mock'),
        );
        setProposalState({ documentId: activeDocument.id, job: nextProposal });
        setInspector('copilot');
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : 'Unable to create proposal.');
      } finally {
        finish('proposal');
      }
    },
    [activeDocument, begin, finish, project, projectId, instruction, setError, setInspector],
  );

  const acceptProposal = useCallback(async () => {
    if (!proposal || !activeDocument || !begin('accept')) return;
    setError(null);
    try {
      await api.acceptProposal(projectId, proposal.id);
      const refreshed = await api.project(projectId);
      setProject(refreshed);
      const refreshedDocument = refreshed.documents?.find((item) => item.id === activeDocument.id);
      if (refreshedDocument) onAccepted(refreshedDocument);
      setProposalState(null);
      loadJobs();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to accept proposal.');
    } finally {
      finish('accept');
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
    acceptProposal,
    pending,
    isRunningProposal: pending.proposal,
    isAcceptingProposal: pending.accept,
    isBusy: pending.proposal || pending.accept,
  };
}
