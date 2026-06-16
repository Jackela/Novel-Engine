import { Download, RotateCcw } from 'lucide-react';

import type { Revision, StudioExport } from '@/app/types/studio';

interface StudioHistoryPanelProps {
  revisions: Revision[];
  loadedRevisionId: string | null;
  exports: StudioExport[];
  onRestoreRevision: (revisionId: string) => void;
}

export function StudioHistoryPanel({
  revisions,
  loadedRevisionId,
  exports,
  onRestoreRevision,
}: StudioHistoryPanelProps) {
  return (
    <div className="inspector-content">
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
                className="icon-command"
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
      {exports.length ? (
        <>
          <h2>Recent exports</h2>
          {exports.slice(0, 4).map((item) => (
            <a className="export-row" href={item.download_url} key={item.id}>
              <Download />
              <span>
                {item.format.toUpperCase()} · {Math.ceil(item.size_bytes / 1024)} KB
              </span>
            </a>
          ))}
        </>
      ) : null}
    </div>
  );
}
