import { RotateCcw } from "lucide-react";
import { useEffect, useRef } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";
import type { RevisionSummary } from "@/app/types/studio";
import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";

interface StudioHistoryPanelProps {
  revisions: RevisionSummary[];
  loadedRevisionId: string | null;
  onRestoreRevision: (revisionId: string) => void | Promise<void>;
  restoringRevisionId?: string | null;
  historyInitialized?: boolean;
  hasOlderRevisions?: boolean;
  isLoadingOlder?: boolean;
  isLoadingHistory?: boolean;
  onLoadOlderRevisions?: () => void | Promise<void>;
}

export function StudioHistoryPanel({
  revisions,
  loadedRevisionId,
  onRestoreRevision,
  restoringRevisionId = null,
  historyInitialized = false,
  hasOlderRevisions = false,
  isLoadingOlder = false,
  isLoadingHistory = false,
  onLoadOlderRevisions,
}: StudioHistoryPanelProps) {
  const isBusy = restoringRevisionId !== null || isLoadingHistory || isLoadingOlder;
  const { t } = useTranslation();
  const runWithFocusRestoration = useCommandFocusRestoration(isBusy);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const restoreButtonRefs = useRef(new Map<string, HTMLButtonElement>());
  const loadOlderButtonRef = useRef<HTMLButtonElement>(null);
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
    if (hasOlderRevisions) {
      const loadButton = loadOlderButtonRef.current;
      if (!loadButton?.isConnected || loadButton.disabled) return;
      loadButton.focus();
    } else {
      const heading = headingRef.current;
      if (!historyInitialized || !heading?.isConnected) return;
      heading.focus();
    }
    keyboardLoadPendingRef.current = false;
    keyboardLoadTriggerRef.current = null;
  }, [hasOlderRevisions, historyInitialized, isBusy]);

  const fallbackFor = (revisionId: string) => {
    for (const [candidateId, button] of restoreButtonRefs.current) {
      if (candidateId !== revisionId && button.isConnected && !button.disabled) return button;
    }
    return headingRef.current;
  };

  return (
    <div aria-busy={isBusy} className="studio-inspector__panel">
      <h2 ref={headingRef} tabIndex={-1}>
        {t("history.heading")}
      </h2>
      <p>{t("history.hint")}</p>
      <div className="studio-inspector__revision-list">
        {revisions.map((revision) => (
          <article key={revision.id}>
            <div>
              <strong>{revision.source}</strong>
              <time>{new Date(revision.created_at).toLocaleString()}</time>
              <small>
                {t("history.row.meta", {
                  count: revision.word_count,
                  unit: revision.word_count === 1 ? t("noun.word") : t("noun.words"),
                  id: revision.id.slice(0, 8),
                })}
              </small>
            </div>
            {revision.id !== loadedRevisionId ? (
              <button
                aria-busy={restoringRevisionId === revision.id}
                aria-label={
                  restoringRevisionId === revision.id
                    ? t("history.row.restoring", { id: revision.id.slice(0, 8) })
                    : t("history.row.restore", { id: revision.id.slice(0, 8) })
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
                title={t("history.row.restoreTitle")}
                type="button"
              >
                <RotateCcw />
              </button>
            ) : (
              <span className="studio-inspector__current-revision">{t("history.row.current")}</span>
            )}
          </article>
        ))}
      </div>
      {(hasOlderRevisions || isLoadingOlder) && onLoadOlderRevisions ? (
        <button
          aria-busy={isLoadingOlder || isLoadingHistory || undefined}
          className="ui-command studio-inspector__load-older"
          disabled={isBusy}
          onClick={(event) => {
            const isKeyboardInvocation = event.detail === 0;
            keyboardLoadPendingRef.current = isKeyboardInvocation;
            keyboardLoadTriggerRef.current = isKeyboardInvocation ? event.currentTarget : null;
            void onLoadOlderRevisions();
          }}
          ref={loadOlderButtonRef}
          type="button"
        >
          {isLoadingOlder
            ? t("history.action.loadingOlder")
            : isLoadingHistory
              ? t("history.status.refreshing")
              : t("history.action.loadOlder")}
        </button>
      ) : isLoadingHistory ? (
        <p className="studio-inspector__history-status" role="status">
          {t("history.status.refreshing")}
        </p>
      ) : historyInitialized ? (
        <p className="studio-inspector__history-status" role="status">
          {t("history.status.allLoaded")}
        </p>
      ) : null}
    </div>
  );
}
