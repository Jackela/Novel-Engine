import { RotateCcw } from 'lucide-react';

import type { Review } from '@/app/types/studio';

interface StudioReviewPanelProps {
  latestReview: Review | null;
  onRunReview: () => void;
  isRunning?: boolean;
}

export function StudioReviewPanel({
  latestReview,
  onRunReview,
  isRunning = false,
}: StudioReviewPanelProps) {
  return (
    <div aria-busy={isRunning} className="inspector-content">
      <header className="inspector-heading">
        <div>
          <h2>Review findings</h2>
          <p>Snapshot-bound and non-mutating.</p>
        </div>
        <button
          aria-busy={isRunning}
          aria-label={isRunning ? 'Running review' : 'Run review'}
          className="icon-command"
          disabled={isRunning}
          onClick={onRunReview}
          title="Run review"
          type="button"
        >
          <RotateCcw />
        </button>
      </header>
      {isRunning ? <p role="status">Running review…</p> : null}
      {latestReview?.issues.length ? (
        latestReview.issues.map((issue) => (
          <article className={`review-issue review-issue--${issue.severity}`} key={issue.id}>
            <header>
              <strong>{issue.code.replace(/_/g, ' ')}</strong>
              <span>{issue.severity}</span>
            </header>
            <p>{issue.message}</p>
            <small>{issue.suggestion}</small>
          </article>
        ))
      ) : (
        <p className="empty-panel">No review findings. Run a review when ready.</p>
      )}
    </div>
  );
}
