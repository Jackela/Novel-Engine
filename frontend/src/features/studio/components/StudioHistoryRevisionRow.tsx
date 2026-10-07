import { RotateCcw } from "lucide-react";
import type { RefObject } from "react";

import { formatDateTime } from "@/app/i18n/format";
import { useTranslation } from "@/app/i18n/useTranslation";
import type { RevisionSummary } from "@/app/types/studio";

import type { RevisionPreviewController, RevisionPreviewScope } from "../hooks/useRevisionPreview";
import { StudioHistoryRevisionPreview } from "./StudioHistoryRevisionPreview";

interface StudioHistoryRevisionRowProps {
  readonly revision: RevisionSummary;
  /** The row's stable short handle for labels and confirmations. */
  readonly shortId: string;
  /** True when this row is the loaded current revision. */
  readonly isCurrent: boolean;
  /** True while this row's restore confirmation is open. */
  readonly isConfirming: boolean;
  /** True while any restore or history load owns the panel. */
  readonly isBusy: boolean;
  readonly restoringRevisionId: string | null;
  /** DR-011 scope; absent renders no preview affordance. */
  readonly previewScope: RevisionPreviewScope | null;
  /** The panel's lazy preview controller (DR-011). */
  readonly preview: RevisionPreviewController;
  /** The panel's live restore-button registry for focus fallback. */
  readonly restoreButtons: Map<string, HTMLButtonElement>;
  /** The confirm button while a row's confirmation is open. */
  readonly confirmButtonRef: RefObject<HTMLButtonElement | null>;
  /** Toggles this row's restore confirmation. */
  readonly onConfirmToggle: () => void;
  /** Cancels this row's restore confirmation. */
  readonly onConfirmCancel: () => void;
  readonly onConfirmRestore: (revisionId: string, target: HTMLButtonElement) => void;
}

/**
 * One revision row: its metadata, the DR-011 read-only preview
 * affordance (rendered only when a preview scope exists), and
 * the two-step restore confirmation. Previewing never restores;
 * opening the confirmation hands focus to the confirm control
 * so a keyboard author reviews the history-preservation warning
 * before firing.
 */
export function StudioHistoryRevisionRow({
  revision,
  shortId,
  isCurrent,
  isConfirming,
  isBusy,
  restoringRevisionId,
  previewScope,
  preview,
  restoreButtons,
  confirmButtonRef,
  onConfirmToggle,
  onConfirmCancel,
  onConfirmRestore,
}: StudioHistoryRevisionRowProps) {
  const { t } = useTranslation();
  const isPreviewOpen = preview.isOpen(revision.id);
  return (
    <div className="studio-inspector__revision-item">
      <article>
        <div>
          <strong>{revision.source}</strong>
          <time>{formatDateTime(revision.created_at)}</time>
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
          {!isCurrent ? (
            <button
              aria-busy={restoringRevisionId === revision.id}
              aria-label={
                restoringRevisionId === revision.id
                  ? t("history.row.restoring", { id: shortId })
                  : t("history.row.restore", { id: shortId })
              }
              className="ui-command--icon"
              disabled={isBusy}
              onClick={() => onConfirmToggle()}
              ref={(node) => {
                if (node) restoreButtons.set(revision.id, node);
                else restoreButtons.delete(revision.id);
              }}
              title={t("history.row.restoreTitle")}
              type="button"
            >
              <RotateCcw />
            </button>
          ) : (
            <span className="studio-inspector__current-revision">{t("history.row.current")}</span>
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
              onClick={(event) => onConfirmRestore(revision.id, event.currentTarget)}
              ref={confirmButtonRef}
              type="button"
            >
              {t("history.restore.confirm")}
            </button>
            <button className="ui-command" onClick={onConfirmCancel} type="button">
              {t("history.restore.cancel")}
            </button>
          </span>
        </div>
      ) : null}
    </div>
  );
}
