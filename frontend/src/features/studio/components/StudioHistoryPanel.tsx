import { useEffect, useRef, useState } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";
import type { RevisionSummary } from "@/app/types/studio";

import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";
import { type RevisionPreviewScope, useRevisionPreview } from "../hooks/useRevisionPreview";
import { StudioHistoryLoadOlder } from "./StudioHistoryLoadOlder";
import { StudioHistoryRevisionRow } from "./StudioHistoryRevisionRow";

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
        {revisions.map((revision) => (
          <StudioHistoryRevisionRow
            key={revision.id}
            confirmButtonRef={confirmButtonRef}
            isBusy={isBusy}
            isConfirming={confirmingRevisionId === revision.id}
            isCurrent={revision.id === loadedRevisionId}
            onConfirmCancel={() => setConfirmingRevisionId(null)}
            onConfirmRestore={confirmRestore}
            onConfirmToggle={() =>
              setConfirmingRevisionId((current) => (current === revision.id ? null : revision.id))
            }
            preview={preview}
            previewScope={previewScope}
            restoreButtons={restoreButtonRefs.current}
            restoringRevisionId={restoringRevisionId}
            revision={revision}
            shortId={revision.id.slice(0, 8)}
          />
        ))}
      </div>
      <StudioHistoryLoadOlder
        keyboardPendingRef={keyboardLoadPendingRef}
        keyboardTriggerRef={keyboardLoadTriggerRef}
        loadButtonRef={loadOlderButtonRef}
        onLoadOlderRevisions={onLoadOlderRevisions}
        status={{
          hasOlderRevisions,
          historyInitialized,
          isBusy,
          isLoadingHistory,
          isLoadingOlder,
        }}
      />
    </div>
  );
}
