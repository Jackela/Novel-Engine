import type { RefObject } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";

/** Whether an older page remains, and which history load currently owns the footer. */
export interface HistoryLoadOlderStatus {
  /** True while an older page remains or a load is in flight. */
  readonly hasOlderRevisions: boolean;
  /** True once the first history page has rendered. */
  readonly historyInitialized: boolean;
  /** True while any restore or history load owns the panel. */
  readonly isBusy: boolean;
  readonly isLoadingHistory: boolean;
  readonly isLoadingOlder: boolean;
}

interface StudioHistoryLoadOlderProps {
  readonly status: HistoryLoadOlderStatus;
  readonly onLoadOlderRevisions?: () => void | Promise<void>;
  /** The load-more button the keyboard-focus effect targets. */
  readonly loadButtonRef: RefObject<HTMLButtonElement | null>;
  /** Keyboard-invocation bookkeeping for the focus-restoration effect. */
  readonly keyboardTriggerRef: RefObject<HTMLButtonElement | null>;
  readonly keyboardPendingRef: RefObject<boolean>;
}

/**
 * Older-revision traversal footer: the load-more command while
 * an older page remains, or the terminal status line. A keyboard
 * invocation (detail 0) records its trigger so the panel's
 * focus-restoration effect can hand focus back when the load
 * settles; a pointer invocation leaves focus alone.
 */
export function StudioHistoryLoadOlder({
  keyboardPendingRef,
  keyboardTriggerRef,
  loadButtonRef,
  onLoadOlderRevisions,
  status,
}: StudioHistoryLoadOlderProps) {
  const { hasOlderRevisions, historyInitialized, isBusy, isLoadingHistory, isLoadingOlder } =
    status;
  const { t } = useTranslation();
  return (hasOlderRevisions || isLoadingOlder) && onLoadOlderRevisions ? (
    <button
      aria-busy={isLoadingOlder || isLoadingHistory || undefined}
      className="ui-command studio-inspector__load-older"
      disabled={isBusy}
      onClick={(event) => {
        const isKeyboardInvocation = event.detail === 0;
        keyboardPendingRef.current = isKeyboardInvocation;
        keyboardTriggerRef.current = isKeyboardInvocation ? event.currentTarget : null;
        void onLoadOlderRevisions();
      }}
      ref={loadButtonRef}
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
  ) : null;
}
