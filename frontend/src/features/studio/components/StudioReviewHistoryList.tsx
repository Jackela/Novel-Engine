import { useEffect, useRef } from "react";

import type { ReviewSummary } from "@/app/types/studio";

interface StudioReviewHistoryListProps {
  summaries: ReviewSummary[];
  historyInitialized: boolean;
  hasOlderReviews: boolean;
  isLoadingOlder: boolean;
  isLoadingHistory: boolean;
  olderError: string | null;
  onLoadOlderReviews: () => void | Promise<void>;
}

/** Bounded review-history summaries with an explicit older-page action (#459). */
export function StudioReviewHistoryList({
  summaries,
  historyInitialized,
  hasOlderReviews,
  isLoadingOlder,
  isLoadingHistory,
  olderError,
  onLoadOlderReviews,
}: StudioReviewHistoryListProps) {
  const isBusy = isLoadingOlder || isLoadingHistory;
  const headingRef = useRef<HTMLHeadingElement | null>(null);
  const loadOlderButtonRef = useRef<HTMLButtonElement | null>(null);
  const keyboardLoadTriggerRef = useRef<HTMLButtonElement | null>(null);
  const keyboardLoadPendingRef = useRef(false);

  useEffect(() => {
    if (isBusy || !keyboardLoadPendingRef.current) return;
    const activeElement = document.activeElement;
    const trigger = keyboardLoadTriggerRef.current;
    const focusWasLost =
      activeElement === null ||
      activeElement === document.body ||
      activeElement === document.documentElement ||
      activeElement === trigger ||
      !activeElement.isConnected;
    if (!focusWasLost) {
      keyboardLoadPendingRef.current = false;
      keyboardLoadTriggerRef.current = null;
      return;
    }
    if (hasOlderReviews) {
      const loadButton = loadOlderButtonRef.current;
      if (!loadButton?.isConnected || loadButton.disabled) return;
      loadButton.focus();
    } else {
      const heading = headingRef.current;
      if (!heading?.isConnected) return;
      heading.focus();
    }
    keyboardLoadPendingRef.current = false;
    keyboardLoadTriggerRef.current = null;
  }, [hasOlderReviews, isBusy]);

  return (
    <section aria-busy={isBusy || undefined} className="studio-inspector__review-history">
      <h3 ref={headingRef} tabIndex={-1}>
        Review history
      </h3>
      {summaries.length ? (
        <ul>
          {summaries.map((summary) => (
            <li key={summary.id}>
              <span>{new Date(summary.created_at).toLocaleString()}</span>
              <small>
                {summary.issue_count} {summary.issue_count === 1 ? "finding" : "findings"} ·{" "}
                {summary.provider}
              </small>
            </li>
          ))}
        </ul>
      ) : historyInitialized ? (
        <p className="studio-inspector__empty">No reviews yet.</p>
      ) : null}
      {olderError ? (
        <div aria-live="assertive" className="studio-inspector__error" role="alert">
          <p>{olderError}</p>
          <button
            className="ui-command"
            disabled={isBusy}
            onClick={() => void onLoadOlderReviews()}
            type="button"
          >
            Try again
          </button>
        </div>
      ) : null}
      {hasOlderReviews ? (
        <button
          aria-busy={isLoadingOlder || undefined}
          className="ui-command"
          disabled={isBusy}
          onClick={(event) => {
            const isKeyboardInvocation = event.detail === 0;
            keyboardLoadPendingRef.current = isKeyboardInvocation;
            keyboardLoadTriggerRef.current = isKeyboardInvocation ? event.currentTarget : null;
            void onLoadOlderReviews();
          }}
          ref={loadOlderButtonRef}
          type="button"
        >
          {isLoadingOlder ? "Loading older reviews…" : "Load older reviews"}
        </button>
      ) : isLoadingOlder ? null : historyInitialized && summaries.length ? (
        <p className="studio-inspector__history-status" role="status">
          All reviews loaded
        </p>
      ) : null}
    </section>
  );
}
