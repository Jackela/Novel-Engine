import { Check, Loader2, X } from "lucide-react";
import type { RefObject } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";
import type { SaveState } from "@/app/types/studio";

import { StudioBodyBudget } from "./StudioBodyBudget";

interface StudioEditorHeaderProps {
  readonly draft: string;
  readonly onTitleChange: (value: string) => void;
  readonly saveState: SaveState;
  readonly titleDraft: string;
  readonly titleRef: RefObject<HTMLInputElement | null>;
  readonly wordCount: number;
}

/**
 * The open Document's chrome: the title field — the conflict
 * command's focus-restoration landing zone, so the pane owns the ref
 * and passes it down — the save-state indicator, the draft word
 * count, and the draft's own body budget (DR-048), ahead of the
 * saved revision.
 */
export function StudioEditorHeader({
  draft,
  onTitleChange,
  saveState,
  titleDraft,
  titleRef,
  wordCount,
}: StudioEditorHeaderProps) {
  const { t } = useTranslation();
  const saveNeedsAttention = saveState === "conflict" || saveState === "error";
  const saveStateLabel =
    saveState === "idle" || saveState === "saved"
      ? t("editor.saveState.saved")
      : saveState === "saving"
        ? t("editor.saveState.saving")
        : saveState === "conflict"
          ? t("editor.saveState.conflict")
          : t("editor.saveState.error");
  return (
    <header className="editor__header">
      <div>
        <input
          aria-label={t("editor.field.title")}
          className="editor__title"
          ref={titleRef}
          value={titleDraft}
          onChange={(event) => onTitleChange(event.target.value)}
        />
        <span
          aria-atomic="true"
          aria-live={saveNeedsAttention ? "assertive" : "polite"}
          className={`editor__save-state editor__save-state--${saveState}`}
          role={saveNeedsAttention ? "alert" : "status"}
        >
          {saveState === "saving" ? (
            <Loader2 aria-hidden="true" className="ui-spin" />
          ) : saveNeedsAttention ? (
            <X aria-hidden="true" />
          ) : (
            <Check aria-hidden="true" />
          )}
          {saveStateLabel}
        </span>
      </div>
      <span className="editor-word-count">
        {t("editor.wordCount", {
          count: wordCount,
          unit: wordCount === 1 ? t("noun.word") : t("noun.words"),
        })}
      </span>
      {/* DR-048: the draft's own budget, ahead of the saved revision. */}
      <StudioBodyBudget draft={draft} />
    </header>
  );
}
