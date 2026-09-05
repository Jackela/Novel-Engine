import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/app/api";
import type { Review, ReviewSummary, ReviewsPage } from "@/app/types/studio";
import type { InspectorTab } from "../studioConstants";
import type { InspectorReviewModel } from "../studioInspectorTypes";

import { toErrorMessage } from "./toErrorMessage";
import { useLazyInspectorResource } from "./useLazyInspectorResource";

interface UseReviewHistoryOptions {
  readonly enabled: boolean;
  readonly inspector: InspectorTab;
  readonly projectId: string;
  readonly recheckProject: (signal: AbortSignal) => Promise<boolean>;
  readonly onSessionLost: () => void;
}

interface OlderRequest {
  readonly controller: AbortController;
  readonly cursor: string;
  readonly epoch: number;
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

function appendUniqueSummaries(current: ReviewsPage, older: ReviewsPage): ReviewsPage {
  const known = new Set(current.reviews.map((summary) => summary.id));
  const uniqueOlder = older.reviews.filter((summary) => {
    if (known.has(summary.id)) return false;
    known.add(summary.id);
    return true;
  });
  return {
    reviews: [...current.reviews, ...uniqueOlder],
    next_cursor: older.next_cursor,
  };
}

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

  const olderRef = useRef<OlderRequest | null>(null);
  const olderEpochRef = useRef(0);
  const [older, setOlder] = useState<{ loading: boolean; error: string | null }>({
    loading: false,
    error: null,
  });

  // Owner switches (project or activation) must abort any in-flight
  // older-page request: without the abort, a late success would append the
  // previous project's summaries onto the new owner's empty first page.
  // biome-ignore lint/correctness/useExhaustiveDependencies: projectId and active are intentional change triggers for this cleanup-only effect; the reset communicates through refs and state, not through reading them.
  useEffect(() => {
    return () => {
      const inFlight = olderRef.current;
      if (inFlight) {
        olderRef.current = null;
        inFlight.controller.abort();
        olderEpochRef.current += 1;
      }
      setOlder({ loading: false, error: null });
    };
  }, [projectId, active]);

  const nextCursor = page.data.next_cursor;
  const isLoadingOlder = older.loading;
  const loadOlder = useCallback((): Promise<void> => {
    if (!active || nextCursor === null || olderRef.current !== null) return Promise.resolve();
    const controller = new AbortController();
    const epoch = ++olderEpochRef.current;
    const cursor = nextCursor;
    olderRef.current = { controller, cursor, epoch };
    setOlder({ loading: true, error: null });
    return (async () => {
      try {
        const olderPage = await api.reviews(projectId, { cursor, signal: controller.signal });
        if (olderRef.current?.epoch !== epoch || controller.signal.aborted) return;
        olderRef.current = null;
        setOlder({ loading: false, error: null });
        page.setData((current) => appendUniqueSummaries(current, olderPage));
      } catch (reason) {
        if (olderRef.current?.epoch !== epoch || controller.signal.aborted) return;
        olderRef.current = null;
        setOlder({
          loading: false,
          error: toErrorMessage(reason, "Unable to load older reviews."),
        });
      }
    })();
  }, [active, page, projectId, nextCursor]);

  const setFirstPage = useCallback(
    (freshPage: ReviewsPage): void => {
      const inFlight = olderRef.current;
      if (inFlight) {
        olderRef.current = null;
        inFlight.controller.abort();
        olderEpochRef.current += 1;
      }
      setOlder({ loading: false, error: null });
      page.setData(freshPage);
    },
    [page],
  );

  // Newest summary identity drives the detail read; the render-phase mirror
  // keeps the stable request closure from observing a stale owner after a
  // project switch.
  const newestReviewId = page.data.reviews[0]?.id ?? null;
  const newestReviewIdRef = useRef<string | null>(newestReviewId);
  newestReviewIdRef.current = newestReviewId;
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
    nextCursor,
    initialized: page.initialized,
    isLoading: page.isLoading,
    error: page.error,
    retry: page.retry,
    setFirstPage,
    isLoadingOlder,
    olderError: older.error,
    loadOlder,
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
    isLoadingHistory: history.isLoading,
    historyError: history.error,
    hasOlderReviews: history.nextCursor !== null,
    isLoadingOlder: history.isLoadingOlder,
    olderError: history.olderError,
    onLoadOlderReviews: history.loadOlder,
    actionError,
    onRetryHistory: history.retry,
    onRunReview,
  };
}
