import { RotateCcw } from "lucide-react";
import { useRef } from "react";

import type { Review } from "@/app/types/studio";
import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";

interface StudioReviewPanelProps {
  latestReview: Review | null;
  historyInitialized?: boolean;
  isLoadingHistory?: boolean;
  historyError?: string | null;
  actionError?: string | null;
  onRetryHistory?: () => void | Promise<void>;
  onRunReview: () => void | Promise<void>;
  isRunning?: boolean;
}

export function StudioReviewPanel({
  latestReview,
  historyInitialized = true,
  isLoadingHistory = false,
  historyError = null,
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
      ) : historyInitialized ? (
        <p className="studio-inspector__empty">No review findings. Run a review when ready.</p>
      ) : null}
    </div>
  );
}
