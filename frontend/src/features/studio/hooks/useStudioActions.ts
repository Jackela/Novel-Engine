import type { Dispatch, SetStateAction } from "react";
import { useCallback, useLayoutEffect, useRef, useState } from "react";

import { api, HttpError } from "@/app/api";
import { clearRetryAttempt, getOrCreateRetryAttemptKey } from "@/app/retryAttemptRegistry";
import type { Project, ReviewsPage } from "@/app/types/studio";
import type { SettingsFormState } from "../studioInspectorTypes";
import { toErrorMessage } from "./toErrorMessage";
import { usePendingAction } from "./usePendingAction";
import { useProjectSettingsUpdate } from "./useProjectSettingsUpdate";
import { useStudioDocumentActions } from "./useStudioDocumentActions";
import type { JobsFreshLoadInitiator } from "./useStudioJobs";
import { useStudioLoreStatusActions } from "./useStudioLoreStatusActions";

interface UseStudioActionsOptions {
  project: Project | null;
  projectId: string;
  setProject: Dispatch<SetStateAction<Project | null>>;
  setReviewPage: (page: ReviewsPage) => void;
  setError: Dispatch<SetStateAction<string | null>>;
  errorPublishers?: Partial<StudioActionErrorPublishers>;
  setActiveId: Dispatch<SetStateAction<string | null>>;
  settingsForm: SettingsFormState;
  setSettingsForm?: Dispatch<SetStateAction<SettingsFormState>>;
  onSettingsSessionLost?: () => void;
  onSettingsProjectMissing?: () => void;
  loadJobs: (initiator?: JobsFreshLoadInitiator) => Promise<void>;
  isProposalActionGated?: () => boolean;
}

export interface StudioActionErrorPublishers {
  readonly review: Dispatch<SetStateAction<string | null>>;
  readonly settings: Dispatch<SetStateAction<string | null>>;
  readonly retryJob: Dispatch<SetStateAction<string | null>>;
  readonly createDocument: Dispatch<SetStateAction<string | null>>;
  readonly moveDocument: Dispatch<SetStateAction<string | null>>;
}

type StudioActionErrorSource = keyof StudioActionErrorPublishers;

const ACTION_KEYS = ["runReview", "retryJob"] as const;

type ActionKey = (typeof ACTION_KEYS)[number];

const DEFINITIVE_RETRY_REJECTIONS = new Set([401, 403, 404, 422]);
const PROPOSAL_ACTIONS_UNGATED = () => false;

interface StudioActionsOwner {
  readonly projectId: string;
  readonly controllers: Set<AbortController>;
  active: boolean;
}

export function useStudioActions({
  project,
  projectId,
  setProject,
  setReviewPage,
  setError,
  errorPublishers,
  setActiveId,
  settingsForm,
  setSettingsForm,
  onSettingsSessionLost,
  onSettingsProjectMissing,
  loadJobs,
  isProposalActionGated = PROPOSAL_ACTIONS_UNGATED,
}: UseStudioActionsOptions) {
  const { pending, begin, finish } = usePendingAction<ActionKey>(ACTION_KEYS);
  const [retryingJobId, setRetryingJobId] = useState<string | null>(null);
  const ownerRef = useRef<StudioActionsOwner | null>(null);

  useLayoutEffect(() => {
    const owner: StudioActionsOwner = {
      projectId,
      controllers: new Set<AbortController>(),
      active: true,
    };
    ownerRef.current = owner;
    return () => {
      owner.active = false;
      for (const controller of owner.controllers) controller.abort();
      owner.controllers.clear();
      if (ownerRef.current === owner) ownerRef.current = null;
    };
  }, [projectId]);

  const currentOwner = useCallback((): StudioActionsOwner | null => {
    const owner = ownerRef.current;
    return owner?.active && owner.projectId === projectId ? owner : null;
  }, [projectId]);

  const isCurrentOwner = useCallback(
    (owner: StudioActionsOwner): boolean => owner.active && ownerRef.current === owner,
    [],
  );

  const publishError = useCallback(
    (owner: StudioActionsOwner, source: StudioActionErrorSource, value: string | null) => {
      if (!isCurrentOwner(owner)) return;
      const publisher = errorPublishers?.[source] ?? setError;
      publisher((current) => (isCurrentOwner(owner) ? value : current));
    },
    [errorPublishers, isCurrentOwner, setError],
  );
  const clearSharedError = useCallback(
    (owner: StudioActionsOwner) => {
      if (!errorPublishers) publishError(owner, "review", null);
    },
    [errorPublishers, publishError],
  );

  const finishForOwner = useCallback(
    (owner: StudioActionsOwner, key: ActionKey) => {
      if (isCurrentOwner(owner)) finish(key);
    },
    [finish, isCurrentOwner],
  );

  const documentActions = useStudioDocumentActions({
    project,
    projectId,
    setProject,
    setActiveId,
    currentOwner,
    isCurrentOwner,
    publishError,
  });
  const loreStatusActions = useStudioLoreStatusActions({
    project,
    projectId,
    setProject,
    currentOwner,
    isCurrentOwner,
    clearSharedError,
  });
  const settingsUpdate = useProjectSettingsUpdate({
    project,
    projectId,
    settingsForm,
    setProject,
    setSettingsForm,
    setSettingsError: errorPublishers?.settings ?? setError,
    onSessionLost: onSettingsSessionLost,
    onProjectMissing: onSettingsProjectMissing,
  });

  const runReview = useCallback(async () => {
    const owner = currentOwner();
    if (!owner || !begin("runReview")) return;
    publishError(owner, "review", null);
    let reviewController: AbortController | null = null;
    try {
      // The synchronous job contract (#272): the response is the terminal
      // review job; one cursorless first-page refresh follows (#459).
      const job = await api.createReview(projectId);
      if (job.status !== "completed") {
        throw new Error(job.error ?? "Unable to run review.");
      }
      if (!isCurrentOwner(owner)) return;
      reviewController = new AbortController();
      owner.controllers.add(reviewController);
      const response = await api.reviews(projectId, { signal: reviewController.signal });
      if (!isCurrentOwner(owner) || reviewController.signal.aborted) return;
      setReviewPage(response);
    } catch (reason) {
      publishError(owner, "review", toErrorMessage(reason, "Unable to run review."));
    } finally {
      if (reviewController) owner.controllers.delete(reviewController);
      finishForOwner(owner, "runReview");
    }
  }, [begin, currentOwner, finishForOwner, isCurrentOwner, projectId, publishError, setReviewPage]);

  const retryJob = useCallback(
    async (jobId: string) => {
      if (isProposalActionGated()) return;
      const owner = currentOwner();
      if (!owner || !begin("retryJob")) return;
      setRetryingJobId(jobId);
      publishError(owner, "retryJob", null);
      let idempotencyKey: string | null = null;
      try {
        idempotencyKey = getOrCreateRetryAttemptKey(projectId, jobId);
        await api.retryJob(projectId, jobId, idempotencyKey);
        clearRetryAttempt(projectId, jobId, idempotencyKey);
        if (!isCurrentOwner(owner)) return;
        await loadJobs("retry");
      } catch (reason) {
        if (
          idempotencyKey !== null &&
          reason instanceof HttpError &&
          DEFINITIVE_RETRY_REJECTIONS.has(reason.status)
        ) {
          clearRetryAttempt(projectId, jobId, idempotencyKey);
        }
        publishError(owner, "retryJob", toErrorMessage(reason, "Unable to retry job."));
      } finally {
        if (isCurrentOwner(owner)) setRetryingJobId(null);
        finishForOwner(owner, "retryJob");
      }
    },
    [
      begin,
      currentOwner,
      finishForOwner,
      isProposalActionGated,
      isCurrentOwner,
      loadJobs,
      projectId,
      publishError,
    ],
  );

  return {
    createDocument: documentActions.createDocument,
    moveDocument: documentActions.moveDocument,
    runReview,
    updateProjectSettings: settingsUpdate.updateProjectSettings,
    retryJob,
    changeLoreStatus: loreStatusActions.changeLoreStatus,
    loreStatusFor: loreStatusActions.loreStatusFor,
    pending: {
      ...documentActions.pending,
      ...pending,
    },
    creatingDocumentKind: documentActions.creatingDocumentKind,
    movingDocument: documentActions.movingDocument,
    isCreatingDocument: documentActions.isCreatingDocument,
    isMovingDocument: documentActions.isMovingDocument,
    isRunningReview: pending.runReview,
    isUpdatingSettings: settingsUpdate.isUpdatingSettings,
    isRetryingJob: pending.retryJob,
    retryingJobId,
  };
}
