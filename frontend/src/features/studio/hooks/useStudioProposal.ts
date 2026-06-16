import { useCallback, useEffect, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';

import { api } from '@/app/api';
import type { InspectorTab } from '@/features/studio/studioConstants';
import type { Project, StudioDocument, StudioJob } from '@/app/types/studio';

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
  const [proposal, setProposal] = useState<StudioJob | null>(null);
  const [instruction, setInstruction] = useState('');

  useEffect(() => {
    setProposal(null);
  }, [activeDocument?.id]);

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
        setProposal(nextProposal);
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
      setProposal(null);
      loadJobs();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to accept proposal.');
    }
  }, [proposal, activeDocument, projectId, setProject, onAccepted, setError, loadJobs]);

  return { proposal, setProposal, instruction, setInstruction, runProposal, acceptProposal };
}
