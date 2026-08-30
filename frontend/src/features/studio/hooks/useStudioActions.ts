import type { Dispatch, FormEvent, SetStateAction } from "react";
import { useCallback, useState } from "react";

import { api } from "@/app/api";
import type { DocumentKind, Project, Review } from "@/app/types/studio";

import { GROUPS, type InspectorTab } from "../studioConstants";

import { toErrorMessage } from "./toErrorMessage";
import { usePendingAction } from "./usePendingAction";

interface UseStudioActionsOptions {
  project: Project | null;
  projectId: string;
  setProject: Dispatch<SetStateAction<Project | null>>;
  setReviews: Dispatch<SetStateAction<Review[]>>;
  setError: Dispatch<SetStateAction<string | null>>;
  setActiveId: Dispatch<SetStateAction<string | null>>;
  setInspector: Dispatch<SetStateAction<InspectorTab>>;
  settingsForm: { title: string; description: string; provider: string };
  loadJobs: () => Promise<void>;
}

const ACTION_KEYS = [
  "createDocument",
  "moveDocument",
  "runReview",
  "updateSettings",
  "retryJob",
] as const;

type ActionKey = (typeof ACTION_KEYS)[number];

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
  const { pending, begin, finish } = usePendingAction<ActionKey>(ACTION_KEYS);
  const [retryingJobId, setRetryingJobId] = useState<string | null>(null);

  const createDocument = useCallback(
    async (kind: DocumentKind) => {
      if (!project || !begin("createDocument")) return;
      const count = project.documents?.filter((document) => document.kind === kind).length ?? 0;
      const label = GROUPS.find((group) => group.kind === kind)?.label ?? "Document";
      setError(null);
      try {
        const document = await api.createDocument(project.id, {
          kind,
          title: kind === "chapter" ? `Chapter ${count + 1}` : `${label} ${count + 1}`,
          content_markdown: kind === "chapter" ? `# Chapter ${count + 1}\n\n` : "",
        });
        setProject((current) =>
          current
            ? {
                ...current,
                documents: [...(current.documents ?? []), document],
              }
            : current,
        );
        setActiveId(document.id);
      } catch (reason) {
        setError(toErrorMessage(reason, "Unable to create document."));
      } finally {
        finish("createDocument");
      }
    },
    [begin, finish, project, setActiveId, setError, setProject],
  );

  const moveDocument = useCallback(
    async (documentId: string, direction: -1 | 1) => {
      if (!project?.documents || !begin("moveDocument")) return;
      const ordered = [...project.documents].sort((a, b) => a.position - b.position);
      const index = ordered.findIndex((document) => document.id === documentId);
      const target = index + direction;
      if (index < 0 || target < 0 || target >= ordered.length) {
        finish("moveDocument");
        return;
      }
      const currentItem = ordered[index];
      const targetItem = ordered[target];
      if (!currentItem || !targetItem) {
        finish("moveDocument");
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
        setError(toErrorMessage(reason, "Unable to reorder documents."));
      } finally {
        finish("moveDocument");
      }
    },
    [begin, finish, project, setError, setProject],
  );

  const runReview = useCallback(async () => {
    if (!begin("runReview")) return;
    setError(null);
    try {
      // The synchronous job contract (#272): the response is the terminal
      // review job; the assessment list is refreshed afterwards.
      const job = await api.createReview(projectId);
      if (job.status !== "completed") {
        throw new Error(job.error ?? "Unable to run review.");
      }
      const response = await api.reviews(projectId);
      setReviews(response.reviews);
      setInspector("review");
    } catch (reason) {
      setError(toErrorMessage(reason, "Unable to run review."));
    } finally {
      finish("runReview");
    }
  }, [begin, finish, projectId, setError, setInspector, setReviews]);

  const updateProjectSettings = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      if (!project || !begin("updateSettings")) return;
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
        setError(toErrorMessage(reason, "Unable to update project."));
      } finally {
        finish("updateSettings");
      }
    },
    [begin, finish, project, settingsForm, setError, setProject],
  );

  const retryJob = useCallback(
    async (jobId: string) => {
      if (!begin("retryJob")) return;
      setRetryingJobId(jobId);
      setError(null);
      try {
        await api.retryJob(projectId, jobId);
        await loadJobs();
      } catch (reason) {
        setError(toErrorMessage(reason, "Unable to retry job."));
      } finally {
        setRetryingJobId(null);
        finish("retryJob");
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
    retryingJobId,
  };
}
