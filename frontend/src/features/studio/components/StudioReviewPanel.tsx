import { RotateCcw } from "lucide-react";
import { useRef } from "react";

import type { Review, ReviewSummary } from "@/app/types/studio";
import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";
import { StudioReviewHistoryList } from "./StudioReviewHistoryList";

interface StudioReviewPanelProps {
  latestReview: Review | null;
  summaries: ReviewSummary[];
  detailLoading?: boolean;
  detailError?: string | null;
  onRetryDetail?: () => void | Promise<void>;
  historyInitialized?: boolean;
  isLoadingHistory?: boolean;
  historyError?: string | null;
  hasOlderReviews?: boolean;
  isLoadingOlder?: boolean;
  olderError?: string | null;
  onLoadOlderReviews?: () => void | Promise<void>;
  actionError?: string | null;
  onRetryHistory?: () => void | Promise<void>;
  onRunReview: () => void | Promise<void>;
  isRunning?: boolean;
}

export function StudioReviewPanel({
  latestReview,
  summaries,
  detailLoading = false,
  detailError = null,
  onRetryDetail,
  historyInitialized = true,
  isLoadingHistory = false,
  historyError = null,
  hasOlderReviews = false,
  isLoadingOlder = false,
  olderError = null,
  onLoadOlderReviews,
  actionError = null,
  onRetryHistory,
  onRunReview,
  isRunning = false,
}: StudioReviewPanelProps) {
  const runWithFocusRestoration = useCommandFocusRestoration(isRunning);
  const retryWithFocusRestoration = useCommandFocusRestoration(isLoadingHistory);
  const headingRef = useRef<HTMLHeadingElement | null>(null);

  return (
    <div aria-busy={isRunning || isLoadingHistory} className="studio-inspector__panel">
      <header className="studio-inspector__heading">
        <div>
          <h2 ref={headingRef} tabIndex={-1}>
            Review findings
          </h2>
          <p>Snapshot-bound and non-mutating.</p>
        </div>
        <button
          aria-busy={isRunning}
          aria-label={isRunning ? "Running review" : "Run review"}
          className="ui-command--icon"
          disabled={isRunning}
          onClick={(event) => {
            void runWithFocusRestoration(event.currentTarget, onRunReview);
          }}
          title="Run review"
          type="button"
        >
          <RotateCcw aria-hidden="true" />
        </button>
      </header>
      {isRunning ? <p role="status">Running review…</p> : null}
      {isLoadingHistory ? <p role="status">Loading review history…</p> : null}
      {historyError ? (
        <div aria-live="assertive" className="studio-inspector__error" role="alert">
          <p>{historyError}</p>
          {onRetryHistory ? (
            <button
              aria-busy={isLoadingHistory || undefined}
              className="ui-command"
              disabled={isLoadingHistory}
              onClick={(event) => {
                void retryWithFocusRestoration(
                  event.currentTarget,
                  onRetryHistory,
                  () => headingRef.current,
                );
              }}
              type="button"
            >
              Try again
            </button>
          ) : null}
        </div>
      ) : null}
      {actionError ? (
        <div aria-live="assertive" className="studio-inspector__error" role="alert">
          {actionError}
        </div>
      ) : null}
      {detailLoading ? <p role="status">Loading review findings…</p> : null}
      {detailError ? (
        <div aria-live="assertive" className="studio-inspector__error" role="alert">
          <p>{detailError}</p>
          {onRetryDetail ? (
            <button className="ui-command" onClick={() => void onRetryDetail()} type="button">
              Try again
            </button>
          ) : null}
        </div>
      ) : null}
      {historyInitialized && latestReview?.issues.length ? (
        latestReview.issues.map((issue) => (
          <article
            className={`studio-inspector__review-issue studio-inspector__review-issue--${issue.severity}`}
            key={issue.id}
          >
            <header>
              <strong>{issue.code.replace(/_/g, " ")}</strong>
              <span>{issue.severity}</span>
            </header>
            <p>{issue.message}</p>
            <small>{issue.suggestion}</small>
          </article>
        ))
      ) : historyInitialized && !detailLoading && !detailError && summaries.length === 0 ? (
        <p className="studio-inspector__empty">No review findings. Run a review when ready.</p>
      ) : null}
      <StudioReviewHistoryList
        hasOlderReviews={hasOlderReviews}
        historyInitialized={historyInitialized}
        isLoadingHistory={isLoadingHistory}
        isLoadingOlder={isLoadingOlder}
        onLoadOlderReviews={onLoadOlderReviews ?? (() => undefined)}
        olderError={olderError}
        summaries={summaries}
      />
    </div>
  );
}
