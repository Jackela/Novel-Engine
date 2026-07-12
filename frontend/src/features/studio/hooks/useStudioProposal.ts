import { useCallback, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';

import { api } from '@/app/api';
import type { InspectorTab } from '@/features/studio/studioConstants';
import type { Project, StudioDocument, StudioJob } from '@/app/types/studio';

interface DocumentProposal {
  readonly documentId: string;
  readonly job: StudioJob;
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
  const activeDocumentId = activeDocument?.id ?? null;
  const proposal = proposalState?.documentId === activeDocumentId ? proposalState.job : null;

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
      if (!activeDocument || !project) return;
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
      }
    },
    [activeDocument, project, projectId, instruction, setError, setInspector],
  );

  const acceptProposal = useCallback(async () => {
    if (!proposal || !activeDocument) return;
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
    }
  }, [proposal, activeDocument, projectId, setProject, onAccepted, setError, loadJobs]);

  return { proposal, setProposal, instruction, setInstruction, runProposal, acceptProposal };
}
