import { RotateCcw } from "lucide-react";

import type { Review } from "@/app/types/studio";
import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";

interface StudioReviewPanelProps {
  latestReview: Review | null;
  onRunReview: () => void | Promise<void>;
  isRunning?: boolean;
}

export function StudioReviewPanel({
  latestReview,
  onRunReview,
  isRunning = false,
}: StudioReviewPanelProps) {
  const runWithFocusRestoration = useCommandFocusRestoration(isRunning);

  return (
    <div aria-busy={isRunning} className="studio-inspector__panel">
      <header className="studio-inspector__heading">
        <div>
          <h2>Review findings</h2>
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
          <RotateCcw />
        </button>
      </header>
      {isRunning ? <p role="status">Running review…</p> : null}
      {latestReview?.issues.length ? (
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
      ) : (
        <p className="studio-inspector__empty">No review findings. Run a review when ready.</p>
      )}
    </div>
  );
}
