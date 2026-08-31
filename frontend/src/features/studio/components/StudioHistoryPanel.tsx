import { RotateCcw } from "lucide-react";
import { useRef } from "react";

import type { Revision } from "@/app/types/studio";
import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";

interface StudioHistoryPanelProps {
  revisions: Revision[];
  loadedRevisionId: string | null;
  onRestoreRevision: (revisionId: string) => void | Promise<void>;
  restoringRevisionId?: string | null;
}

export function StudioHistoryPanel({
  revisions,
  loadedRevisionId,
  onRestoreRevision,
  restoringRevisionId = null,
}: StudioHistoryPanelProps) {
  const isBusy = restoringRevisionId !== null;
  const runWithFocusRestoration = useCommandFocusRestoration(isBusy);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const restoreButtonRefs = useRef(new Map<string, HTMLButtonElement>());

  const fallbackFor = (revisionId: string) => {
    for (const [candidateId, button] of restoreButtonRefs.current) {
      if (candidateId !== revisionId && button.isConnected && !button.disabled) return button;
    }
    return headingRef.current;
  };

  return (
    <div aria-busy={isBusy} className="studio-inspector__panel">
      <h2 ref={headingRef} tabIndex={-1}>
        Revision history
      </h2>
      <p>Restoring creates a new revision and preserves the chain.</p>
      <div className="studio-inspector__revision-list">
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
                className="ui-command--icon"
                disabled={isBusy}
                onClick={(event) => {
                  void runWithFocusRestoration(
                    event.currentTarget,
                    () => onRestoreRevision(revision.id),
                    () => fallbackFor(revision.id),
                  );
                }}
                ref={(node) => {
                  if (node) restoreButtonRefs.current.set(revision.id, node);
                  else restoreButtonRefs.current.delete(revision.id);
                }}
                title="Restore revision"
                type="button"
              >
                <RotateCcw />
              </button>
            ) : (
              <span className="studio-inspector__current-revision">Current</span>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
