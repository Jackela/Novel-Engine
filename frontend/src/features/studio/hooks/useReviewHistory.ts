import { useCallback, useEffect, useRef } from "react";

import { api } from "@/app/api";
import type { Review, ReviewSummary, ReviewsPage } from "@/app/types/studio";
import type { InspectorTab } from "../studioConstants";
import type { InspectorReviewModel } from "../studioInspectorTypes";

import { appendUniqueById, useKeysetOlderPages } from "./keysetHistory";
import { useLazyInspectorResource } from "./useLazyInspectorResource";

interface UseReviewHistoryOptions {
  readonly enabled: boolean;
  readonly inspector: InspectorTab;
  readonly projectId: string;
  readonly recheckProject: (signal: AbortSignal) => Promise<boolean>;
  readonly onSessionLost: () => void;
}

export interface ReviewDetailState {
  readonly review: Review | null;
  readonly isLoading: boolean;
  readonly error: string | null;
  readonly retry: () => Promise<void>;
}

export interface ReviewHistoryState {
  readonly summaries: ReviewSummary[];
  readonly nextCursor: string | null;
  readonly initialized: boolean;
  readonly isLoading: boolean;
  readonly error: string | null;
  readonly retry: () => Promise<void>;
  readonly setFirstPage: (page: ReviewsPage) => void;
  readonly isLoadingOlder: boolean;
  readonly olderError: string | null;
  readonly loadOlder: () => Promise<void>;
  readonly detail: ReviewDetailState;
}

const EMPTY_PAGE: ReviewsPage = { reviews: [], next_cursor: null };

/**
 * One URL-selected Review history: bounded first summary page, explicit older
 * traversal, and one lazy detail read of the newest assessment (#459).
 */
export function useReviewHistory({
  enabled,
  inspector,
  projectId,
  recheckProject,
  onSessionLost,
}: UseReviewHistoryOptions): ReviewHistoryState {
  const active = enabled && inspector === "review";
  const requestPage = useCallback(
    (signal: AbortSignal) => api.reviews(projectId, { signal }),
    [projectId],
  );
  const page = useLazyInspectorResource<ReviewsPage>({
    active,
    projectId,
    empty: EMPTY_PAGE,
    request: requestPage,
    recheckProject,
    onSessionLost,
    missingResourceMessage: "Review history is unavailable for this project.",
    loadErrorMessage: "Unable to load review history.",
  });

  const olderPages = useKeysetOlderPages<ReviewsPage>({
    cleanupKey: `${projectId}:${active}`,
    isEnabled: () => active,
    nextCursor: page.data.next_cursor,
    fetchPage: (cursor, signal) => api.reviews(projectId, { cursor, signal }),
    commitPage: (olderPage) =>
      page.setData((current) => ({
        reviews: appendUniqueById(current.reviews, olderPage.reviews, (summary) => summary.id),
        next_cursor: olderPage.next_cursor,
      })),
    busyErrorMessage: "Unable to load older reviews.",
  });
  const abortInFlightOlder = olderPages.abortInFlight;

  const setFirstPage = useCallback(
    (freshPage: ReviewsPage): void => {
      abortInFlightOlder();
      page.setData(freshPage);
    },
    [abortInFlightOlder, page],
  );

  // Newest summary identity drives the detail read; the commit-phase mirror
  // keeps the stable request closure from observing a stale owner after a
  // project switch. It syncs in an effect declared before the detail read's
  // own effects, so every request initiation below observes fresh state.
  const newestReviewId = page.data.reviews[0]?.id ?? null;
  const newestReviewIdRef = useRef<string | null>(newestReviewId);
  useEffect(() => {
    newestReviewIdRef.current = newestReviewId;
  }, [newestReviewId]);
  const requestedDetailIdRef = useRef<string | null>(null);
  const requestDetail = useCallback(
    (signal: AbortSignal): Promise<Review | null> => {
      const reviewId = newestReviewIdRef.current;
      return reviewId === null
        ? Promise.resolve(null)
        : api.reviewDetail(projectId, reviewId, { signal });
    },
    [projectId],
  );
  const detail = useLazyInspectorResource<Review | null>({
    active,
    projectId,
    empty: null,
    request: requestDetail,
    recheckProject,
    onSessionLost,
    missingResourceMessage: "Review findings are unavailable for this review.",
    loadErrorMessage: "Unable to load review findings.",
  });

  useEffect(() => {
    if (!active || newestReviewId === null) return;
    if (requestedDetailIdRef.current === newestReviewId) return;
    requestedDetailIdRef.current = newestReviewId;
    void detail.retry();
  }, [active, detail, newestReviewId]);

  return {
    summaries: page.data.reviews,
    nextCursor: page.data.next_cursor,
    initialized: page.initialized,
    isLoading: page.isLoading,
    error: page.error,
    retry: page.retry,
    setFirstPage,
    isLoadingOlder: olderPages.isLoadingOlder,
    olderError: olderPages.olderError,
    loadOlder: olderPages.loadOlder,
    detail: {
      review: detail.data,
      isLoading: active && detail.isLoading,
      error: detail.error,
      retry: detail.retry,
    },
  };
}

/** Assemble the Inspector review-tab model from one review-history state (#459). */
export function reviewInspectorModel(
  history: ReviewHistoryState,
  actionError: string | null,
  onRunReview: () => void | Promise<void>,
): InspectorReviewModel {
  return {
    latestReview: history.detail.review,
    detailLoading: history.detail.isLoading,
    detailError: history.detail.error,
    onRetryDetail: history.detail.retry,
    summaries: history.summaries,
    historyInitialized: history.initialized,
    historyPaging: {
      isLoading: history.isLoading,
      hasOlder: history.nextCursor !== null,
      isLoadingOlder: history.isLoadingOlder,
    },
    historyError: history.error,
    olderError: history.olderError,
    onLoadOlderReviews: history.loadOlder,
    actionError,
    onRetryHistory: history.retry,
    onRunReview,
  };
}
