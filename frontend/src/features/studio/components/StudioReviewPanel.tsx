import { RotateCcw } from 'lucide-react';

import type { Review } from '@/app/types/studio';

interface StudioReviewPanelProps {
  latestReview: Review | null;
  onRunReview: () => void;
}

export function StudioReviewPanel({ latestReview, onRunReview }: StudioReviewPanelProps) {
  return (
    <div className="inspector-content">
      <header className="inspector-heading">
        <div>
          <h2>Review findings</h2>
          <p>Snapshot-bound and non-mutating.</p>
        </div>
        <button className="icon-command" onClick={onRunReview} title="Run review" type="button">
          <RotateCcw />
        </button>
      </header>
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
