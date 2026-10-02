import { RotateCcw } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";
import type { RevisionSummary } from "@/app/types/studio";

import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";
import { type RevisionPreviewScope, useRevisionPreview } from "../hooks/useRevisionPreview";
import { StudioHistoryRevisionPreview } from "./StudioHistoryRevisionPreview";

interface StudioHistoryPanelProps {
  revisions: RevisionSummary[];
  loadedRevisionId: string | null;
  onRestoreRevision: (revisionId: string) => void | Promise<void>;
  /**
   * DR-011: project/document scope plus the loaded current body a row's
   * read-only preview and diff need. Absent scope renders no preview
   * affordance (isolated fixtures without a live document).
   */
  previewScope?: RevisionPreviewScope | null;
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
  previewScope = null,
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
  const confirmButtonRef = useRef<HTMLButtonElement | null>(null);
  const loadOlderButtonRef = useRef<HTMLButtonElement>(null);
  const keyboardLoadTriggerRef = useRef<HTMLButtonElement | null>(null);
  const keyboardLoadPendingRef = useRef(false);
  const [confirmingRevisionId, setConfirmingRevisionId] = useState<string | null>(null);
  const preview = useRevisionPreview(previewScope);

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

  // Opening a row's restore confirmation hands focus to the confirm control,
  // so a keyboard author reviews the history-preservation warning before firing.
  useEffect(() => {
    if (confirmingRevisionId !== null) confirmButtonRef.current?.focus();
  }, [confirmingRevisionId]);

  const fallbackFor = (revisionId: string) => {
    for (const [candidateId, button] of restoreButtonRefs.current) {
      if (candidateId !== revisionId && button.isConnected && !button.disabled) return button;
    }
    return headingRef.current;
  };

  const confirmRestore = (revisionId: string, target: HTMLButtonElement) => {
    setConfirmingRevisionId(null);
    void runWithFocusRestoration(
      target,
      () => onRestoreRevision(revisionId),
      () => fallbackFor(revisionId),
    );
  };

  return (
    <div aria-busy={isBusy} className="studio-inspector__panel">
      <h2 ref={headingRef} tabIndex={-1}>
        {t("history.heading")}
      </h2>
      <p>{t("history.hint")}</p>
      <div className="studio-inspector__revision-list">
        {revisions.map((revision) => {
          const shortId = revision.id.slice(0, 8);
          const isConfirming = confirmingRevisionId === revision.id;
          const isPreviewOpen = preview.isOpen(revision.id);
          return (
            <div className="studio-inspector__revision-item" key={revision.id}>
              <article>
                <div>
                  <strong>{revision.source}</strong>
                  <time>{new Date(revision.created_at).toLocaleString()}</time>
                  <small>
                    {t("history.row.meta", {
                      count: revision.word_count,
                      unit: revision.word_count === 1 ? t("noun.word") : t("noun.words"),
                      id: shortId,
                    })}
                  </small>
                </div>
                <div className="studio-inspector__revision-actions">
                  {previewScope ? (
                    <button
                      aria-controls={`history-preview-${revision.id}`}
                      aria-expanded={isPreviewOpen}
                      className="ui-command"
                      onClick={() => preview.toggle(revision.id)}
                      type="button"
                    >
                      {isPreviewOpen ? t("history.row.previewHide") : t("history.row.preview")}
                    </button>
                  ) : null}
                  {revision.id !== loadedRevisionId ? (
                    <button
                      aria-busy={restoringRevisionId === revision.id}
                      aria-label={
                        restoringRevisionId === revision.id
                          ? t("history.row.restoring", { id: shortId })
                          : t("history.row.restore", { id: shortId })
                      }
                      className="ui-command--icon"
                      disabled={isBusy}
                      onClick={() =>
                        setConfirmingRevisionId((current) =>
                          current === revision.id ? null : revision.id,
                        )
                      }
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
                    <span className="studio-inspector__current-revision">
                      {t("history.row.current")}
                    </span>
                  )}
                </div>
              </article>
              {isPreviewOpen && previewScope ? (
                <div id={`history-preview-${revision.id}`}>
                  <StudioHistoryRevisionPreview
                    currentContent={previewScope.currentContent}
                    onRetry={() => preview.retry(revision.id)}
                    revision={revision}
                    state={preview.stateFor(revision.id)}
                  />
                </div>
              ) : null}
              {isConfirming ? (
                <div className="studio-inspector__restore-confirm">
                  <p>{t("history.restore.confirmBody", { id: shortId })}</p>
                  <span className="studio-inspector__restore-confirm-actions">
                    <button
                      className="ui-command"
                      onClick={(event) => confirmRestore(revision.id, event.currentTarget)}
                      ref={confirmButtonRef}
                      type="button"
                    >
                      {t("history.restore.confirm")}
                    </button>
                    <button
                      className="ui-command"
                      onClick={() => setConfirmingRevisionId(null)}
                      type="button"
                    >
                      {t("history.restore.cancel")}
                    </button>
                  </span>
                </div>
              ) : null}
            </div>
          );
        })}
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
