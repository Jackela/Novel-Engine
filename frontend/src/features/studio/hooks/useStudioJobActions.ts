import { useCallback, useState } from "react";

import { api, HttpError } from "@/app/api";
import { translateActive } from "@/app/i18n/translate";
import { clearRetryAttempt, getOrCreateRetryAttemptKey } from "@/app/retryAttemptRegistry";
import type { ReviewsPage } from "@/app/types/studio";
import { toErrorMessage } from "./toErrorMessage";
import { usePendingAction } from "./usePendingAction";
import type { StudioActionsOwner } from "./useStudioActionOwner";
import type { JobsFreshLoadInitiator } from "./useStudioJobs";

const ACTION_KEYS = ["runReview", "retryJob"] as const;

type ActionKey = (typeof ACTION_KEYS)[number];

type JobActionErrorSource = "review" | "retryJob";

const DEFINITIVE_RETRY_REJECTIONS = new Set([401, 403, 404, 422]);

interface UseStudioJobActionsOptions {
  readonly projectId: string;
  readonly currentOwner: () => StudioActionsOwner | null;
  readonly isCurrentOwner: (owner: StudioActionsOwner) => boolean;
  readonly publishError: (
    owner: StudioActionsOwner,
    source: JobActionErrorSource,
    value: string | null,
  ) => void;
  readonly setReviewPage: (page: ReviewsPage) => void;
  readonly loadJobs: (initiator?: JobsFreshLoadInitiator) => Promise<void>;
  readonly isProposalActionGated: () => boolean;
}

/**
 * Review and retry-job commands with their job-domain state: pending gating,
 * the retrying job identity, per-owner scoped error publication, and retry
 * idempotency keys.
 */
export function useStudioJobActions({
  projectId,
  currentOwner,
  isCurrentOwner,
  publishError,
  setReviewPage,
  loadJobs,
  isProposalActionGated,
}: UseStudioJobActionsOptions) {
  const { pending, begin, finish } = usePendingAction<ActionKey>(ACTION_KEYS);
  const [retryingJobId, setRetryingJobId] = useState<string | null>(null);

  const finishForOwner = useCallback(
    (owner: StudioActionsOwner, key: ActionKey) => {
      if (isCurrentOwner(owner)) finish(key);
    },
    [finish, isCurrentOwner],
  );

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
        throw new Error(job.error ?? translateActive("errors.runReview"));
      }
      if (!isCurrentOwner(owner)) return;
      reviewController = new AbortController();
      owner.controllers.add(reviewController);
      const response = await api.reviews(projectId, { signal: reviewController.signal });
      if (!isCurrentOwner(owner) || reviewController.signal.aborted) return;
      setReviewPage(response);
    } catch (reason) {
      publishError(owner, "review", toErrorMessage(reason, translateActive("errors.runReview")));
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
        publishError(owner, "retryJob", toErrorMessage(reason, translateActive("errors.retryJob")));
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

  return { runReview, retryJob, retryingJobId, pending };
}
