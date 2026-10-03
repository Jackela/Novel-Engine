import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/app/api";
import { translateActive } from "@/app/i18n/translate";
import type { Review, ReviewSummary, ReviewsPage } from "@/app/types/studio";
import type { InspectorReviewModel } from "../studioInspectorTypes";
import { appendUniqueById, useKeysetOlderPages } from "./keysetHistory";
import { useLazyInspectorResource } from "./useLazyInspectorResource";

interface UseReviewHistoryOptions {
  readonly active: boolean;
  readonly projectId: string;
  readonly recheckProject: (signal: AbortSignal) => Promise<boolean>;
  readonly onSessionLost: () => void;
}

interface ReviewDetailState {
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
  /**
   * The summary whose detail is on screen (DR-042): the explicitly selected
   * review, or the newest summary while nothing is selected.
   */
  readonly selectedReviewId: string | null;
  /** Open one history row's detail; a null request falls back to the newest. */
  readonly selectReview: (reviewId: string | null) => void;
  readonly detail: ReviewDetailState;
}

const EMPTY_PAGE: ReviewsPage = { reviews: [], next_cursor: null };

/**
 * One Review history family member: bounded first summary page, explicit
 * older traversal, and one lazy detail read — the newest assessment by
 * default, or the row the author selected (DR-042). Activation arrives
 * pre-derived from `useLazyInspectorHistories`.
 */
export function useReviewHistory({
  active,
  projectId,
  recheckProject,
  onSessionLost,
}: UseReviewHistoryOptions): ReviewHistoryState {
  const [selectedReviewId, setSelectedReviewId] = useState<string | null>(null);
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
    missingResourceMessage: translateActive("errors.missingReviewHistory"),
    loadErrorMessage: translateActive("errors.loadReviewHistory"),
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
    busyErrorMessage: translateActive("errors.loadOlderReviews"),
  });
  const abortInFlightOlder = olderPages.abortInFlight;

  const setFirstPage = useCallback(
    (freshPage: ReviewsPage): void => {
      abortInFlightOlder();
      // A fresh first page is a new review era; the newest detail shows again.
      setSelectedReviewId(null);
      page.setData(freshPage);
    },
    [abortInFlightOlder, page],
  );

  // Newest summary identity drives the default detail read; an explicit row
  // selection (DR-042) overrides it until the next fresh first page. The
  // commit-phase mirror keeps the stable request closure from observing a
  // stale owner after a project switch. It syncs in an effect declared
  // before the detail read's own effects, so every request initiation below
  // observes fresh state.
  const newestReviewId = page.data.reviews[0]?.id ?? null;
  const activeReviewId = selectedReviewId ?? newestReviewId;
  const activeReviewIdRef = useRef<string | null>(activeReviewId);
  useEffect(() => {
    activeReviewIdRef.current = activeReviewId;
  }, [activeReviewId]);
  const requestedDetailIdRef = useRef<string | null>(null);
  const requestDetail = useCallback(
    (signal: AbortSignal): Promise<Review | null> => {
      const reviewId = activeReviewIdRef.current;
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
    missingResourceMessage: translateActive("errors.missingReviewFindings"),
    loadErrorMessage: translateActive("errors.loadReviewFindings"),
  });

  useEffect(() => {
    if (!active || activeReviewId === null) return;
    if (requestedDetailIdRef.current === activeReviewId) return;
    requestedDetailIdRef.current = activeReviewId;
    // `load()` reuses an in-flight read, so a pending detail for the previous
    // selection is dropped first; the cleared slot also keeps the previous
    // review's issues from rendering under the newly selected row.
    detail.setData(null);
    void detail.retry();
  }, [active, activeReviewId, detail]);

  /** Row activation (DR-042); null returns the panel to the newest review. */
  const selectReview = useCallback((reviewId: string | null): void => {
    setSelectedReviewId(reviewId);
  }, []);

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
    selectedReviewId: activeReviewId,
    selectReview,
    detail: {
      review: detail.data,
      isLoading: active && detail.isLoading,
      error: detail.error,
      retry: detail.retry,
    },
  };
}

/** Assemble the Inspector review-tab model from one review-history state (#459, DR-042). */
export function reviewInspectorModel(
  history: ReviewHistoryState,
  actionError: string | null,
  onRunReview: () => void | Promise<void>,
): InspectorReviewModel {
  return {
    selectedReview: history.detail.review,
    selectedReviewId: history.selectedReviewId,
    onSelectReview: history.selectReview,
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
