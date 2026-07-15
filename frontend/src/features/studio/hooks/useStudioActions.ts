import { useCallback, useRef, useState } from 'react';
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

type ActionKey = 'createDocument' | 'moveDocument' | 'runReview' | 'updateSettings' | 'retryJob';

interface PendingActions {
  readonly createDocument: boolean;
  readonly moveDocument: boolean;
  readonly runReview: boolean;
  readonly updateSettings: boolean;
  readonly retryJob: boolean;
}

const INITIAL_PENDING: PendingActions = {
  createDocument: false,
  moveDocument: false,
  runReview: false,
  updateSettings: false,
  retryJob: false,
};

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
  const [pending, setPending] = useState<PendingActions>(INITIAL_PENDING);
  const pendingRef = useRef<Set<ActionKey> | null>(null);

  const begin = useCallback((key: ActionKey) => {
    const current = pendingRef.current ?? (pendingRef.current = new Set<ActionKey>());
    if (current.has(key)) return false;
    current.add(key);
    setPending((current) => ({ ...current, [key]: true }));
    return true;
  }, []);

  const finish = useCallback((key: ActionKey) => {
    pendingRef.current?.delete(key);
    setPending((current) => ({ ...current, [key]: false }));
  }, []);

  const createDocument = useCallback(
    async (kind: DocumentKind) => {
      if (!project || !begin('createDocument')) return;
      const count = project.documents?.filter((document) => document.kind === kind).length ?? 0;
      const label = GROUPS.find((group) => group.kind === kind)?.label ?? 'Document';
      setError(null);
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
      } finally {
        finish('createDocument');
      }
    },
    [begin, finish, project, setActiveId, setError, setProject],
  );

  const moveDocument = useCallback(
    async (documentId: string, direction: -1 | 1) => {
      if (!project?.documents || !begin('moveDocument')) return;
      const ordered = [...project.documents].sort((a, b) => a.position - b.position);
      const index = ordered.findIndex((document) => document.id === documentId);
      const target = index + direction;
      if (index < 0 || target < 0 || target >= ordered.length) {
        finish('moveDocument');
        return;
      }
      const currentItem = ordered[index];
      const targetItem = ordered[target];
      if (!currentItem || !targetItem) {
        finish('moveDocument');
        return;
      }
      ordered[index] = targetItem;
      ordered[target] = currentItem;
      setError(null);
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
      } finally {
        finish('moveDocument');
      }
    },
    [begin, finish, project, setError, setProject],
  );

  const runReview = useCallback(async () => {
    if (!begin('runReview')) return;
    setError(null);
    try {
      const review = await api.createReview(projectId);
      setReviews((current) => [review, ...current]);
      setInspector('review');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to run review.');
    } finally {
      finish('runReview');
    }
  }, [begin, finish, projectId, setError, setInspector, setReviews]);

  const updateProjectSettings = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      if (!project || !begin('updateSettings')) return;
      setError(null);
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
      } finally {
        finish('updateSettings');
      }
    },
    [begin, finish, project, settingsForm, setError, setProject],
  );

  const retryJob = useCallback(
    async (jobId: string) => {
      if (!begin('retryJob')) return;
      setError(null);
      try {
        await api.retryJob(projectId, jobId);
        void loadJobs();
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : 'Unable to retry job.');
      } finally {
        finish('retryJob');
      }
    },
    [begin, finish, projectId, loadJobs, setError],
  );

  return {
    createDocument,
    moveDocument,
    runReview,
    updateProjectSettings,
    retryJob,
    pending,
    isCreatingDocument: pending.createDocument,
    isMovingDocument: pending.moveDocument,
    isRunningReview: pending.runReview,
    isUpdatingSettings: pending.updateSettings,
    isRetryingJob: pending.retryJob,
    isBusy: Object.values(pending).some(Boolean),
  };
}
