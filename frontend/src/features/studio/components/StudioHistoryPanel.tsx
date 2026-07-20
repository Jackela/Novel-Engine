import { RotateCcw } from 'lucide-react';

import type { Revision } from '@/app/types/studio';

interface StudioHistoryPanelProps {
  revisions: Revision[];
  loadedRevisionId: string | null;
  onRestoreRevision: (revisionId: string) => void;
  restoringRevisionId?: string | null;
}

export function StudioHistoryPanel({
  revisions,
  loadedRevisionId,
  onRestoreRevision,
  restoringRevisionId = null,
}: StudioHistoryPanelProps) {
  const isBusy = restoringRevisionId !== null;

  return (
    <div aria-busy={isBusy} className="inspector-content">
      <h2>Revision history</h2>
      <p>Restoring creates a new revision and preserves the chain.</p>
      <div className="revision-list">
        {revisions.map((revision) => (
          <article key={revision.id}>
            <div>
              <strong>{revision.source}</strong>
              <time>{new Date(revision.created_at).toLocaleString()}</time>
              <small>
                {revision.word_count} words · {revision.id.slice(0, 8)}
              </small>
            </div>
            {revision.id !== loadedRevisionId ? (
              <button
                aria-busy={restoringRevisionId === revision.id}
                aria-label={
                  restoringRevisionId === revision.id
                    ? `Restoring revision ${revision.id.slice(0, 8)}`
                    : `Restore revision ${revision.id.slice(0, 8)}`
                }
                className="icon-command"
                disabled={isBusy}
                onClick={() => onRestoreRevision(revision.id)}
                title="Restore revision"
                type="button"
              >
                <RotateCcw />
              </button>
            ) : (
              <span className="current-revision">Current</span>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
