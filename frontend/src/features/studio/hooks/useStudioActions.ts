import { useCallback } from 'react';
import type { Dispatch, FormEvent, SetStateAction } from 'react';

import { api } from '@/app/api';
import type { DocumentKind, Project, Review } from '@/app/types/studio';

import { GROUPS, type InspectorTab } from '../studioConstants';

interface UseStudioActionsOptions {
  project: Project | null;
  projectId: string;
  setProject: Dispatch<SetStateAction<Project | null>>;
  setReviews: Dispatch<SetStateAction<Review[]>>;
  setError: Dispatch<SetStateAction<string | null>>;
  setActiveId: Dispatch<SetStateAction<string | null>>;
  setInspector: Dispatch<SetStateAction<InspectorTab>>;
  settingsForm: { title: string; description: string; provider: string };
  loadJobs: () => void;
}

export function useStudioActions({
  project,
  projectId,
  setProject,
  setReviews,
  setError,
  setActiveId,
  setInspector,
  settingsForm,
  loadJobs,
}: UseStudioActionsOptions) {
  const createDocument = useCallback(
    async (kind: DocumentKind) => {
      if (!project) return;
      const count = project.documents?.filter((document) => document.kind === kind).length ?? 0;
      const label = GROUPS.find((group) => group.kind === kind)?.label ?? 'Document';
      try {
        const document = await api.createDocument(project.id, {
          kind,
          title: kind === 'chapter' ? `Chapter ${count + 1}` : `${label} ${count + 1}`,
          content_markdown: kind === 'chapter' ? `# Chapter ${count + 1}\n\n` : '',
        });
        setProject((current) =>
          current ? { ...current, documents: [...(current.documents ?? []), document] } : current,
        );
        setActiveId(document.id);
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : 'Unable to create document.');
      }
    },
    [project, setActiveId, setError, setProject],
  );

  const moveDocument = useCallback(
    async (documentId: string, direction: -1 | 1) => {
      if (!project?.documents) return;
      const ordered = [...project.documents].sort((a, b) => a.position - b.position);
      const index = ordered.findIndex((document) => document.id === documentId);
      const target = index + direction;
      if (index < 0 || target < 0 || target >= ordered.length) return;
      const currentItem = ordered[index];
      const targetItem = ordered[target];
      if (!currentItem || !targetItem) return;
      ordered[index] = targetItem;
      ordered[target] = currentItem;
      try {
        const response = await api.reorderDocuments(
          project.id,
          ordered.map((item) => item.id),
        );
        setProject((current) =>
          current ? { ...current, documents: response.documents } : current,
        );
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : 'Unable to reorder documents.');
      }
    },
    [project, setError, setProject],
  );

  const runReview = useCallback(async () => {
    try {
      const review = await api.createReview(projectId);
      setReviews((current) => [review, ...current]);
      setInspector('review');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to run review.');
    }
  }, [projectId, setError, setInspector, setReviews]);

  const updateProjectSettings = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      if (!project) return;
      try {
        const updated = await api.updateProject(project.id, {
          title: settingsForm.title,
          description: settingsForm.description,
          settings: { ...project.settings, provider: settingsForm.provider },
        });
        setProject(updated);
        setError(null);
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : 'Unable to update project.');
      }
    },
    [project, settingsForm, setError, setProject],
  );

  const retryJob = useCallback(
    async (jobId: string) => {
      try {
        await api.retryJob(projectId, jobId);
        void loadJobs();
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : 'Unable to retry job.');
      }
    },
    [projectId, loadJobs, setError],
  );

  return { createDocument, moveDocument, runReview, updateProjectSettings, retryJob };
}
