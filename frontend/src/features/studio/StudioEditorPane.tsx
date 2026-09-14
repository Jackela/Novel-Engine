import { Check, Loader2, X } from "lucide-react";
import { lazy, Suspense, useRef, useState } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";
import type { SaveState, StudioDocument } from "@/app/types/studio";
import { useCommandFocusRestoration } from "./hooks/useCommandFocusRestoration";

const MarkdownEditor = lazy(async () => {
  const module = await import("./MarkdownEditor");
  return { default: module.MarkdownEditor };
});

interface StudioEditorPaneProps {
  activeDocument: StudioDocument | null;
  draft: string;
  titleDraft: string;
  saveState: SaveState;
  error?: string | null;
  isConflictActionPending?: boolean;
  isLoadingDocument?: boolean;
  documentLoadError?: string | null;
  onDraftChange: (value: string) => void;
  onTitleChange: (value: string) => void;
  onLoadLatest?: () => void | Promise<void>;
  onRetryOverwrite?: () => void | Promise<void>;
  onRetryDocument?: () => void;
}

export function StudioEditorPane({
  activeDocument,
  draft,
  titleDraft,
  saveState,
  error = null,
  isConflictActionPending = false,
  isLoadingDocument = false,
  documentLoadError = null,
  onDraftChange,
  onTitleChange,
  onLoadLatest,
  onRetryOverwrite,
  onRetryDocument,
}: StudioEditorPaneProps) {
  const { t } = useTranslation();
  const titleRef = useRef<HTMLInputElement>(null);
  const pendingCommandRef = useRef<"loadLatest" | "retryOverwrite" | null>(null);
  const [pendingCommand, setPendingCommand] = useState<"loadLatest" | "retryOverwrite" | null>(
    null,
  );
  const saveNeedsAttention = saveState === "conflict" || saveState === "error";
  const conflictActionsDisabled =
    pendingCommand !== null || isConflictActionPending || saveState === "saving";
  const saveStateLabel =
    saveState === "idle" || saveState === "saved"
      ? t("editor.saveState.saved")
      : saveState === "saving"
        ? t("editor.saveState.saving")
        : saveState === "conflict"
          ? t("editor.saveState.conflict")
          : t("editor.saveState.error");
  const runWithFocusRestoration = useCommandFocusRestoration(conflictActionsDisabled);

  const runConflictCommand = (
    commandKey: "loadLatest" | "retryOverwrite",
    target: HTMLButtonElement,
    command: (() => void | Promise<void>) | undefined,
  ) => {
    if (command === undefined || conflictActionsDisabled || pendingCommandRef.current !== null)
      return;
    pendingCommandRef.current = commandKey;
    setPendingCommand(commandKey);
    void runWithFocusRestoration(
      target,
      async () => {
        try {
          await command();
        } finally {
          if (pendingCommandRef.current === commandKey) pendingCommandRef.current = null;
          setPendingCommand((current) => (current === commandKey ? null : current));
        }
      },
      () => titleRef.current,
    );
  };

  return (
    <section
      aria-busy={isLoadingDocument || isConflictActionPending || saveState === "saving"}
      className="studio-editor"
    >
      {activeDocument ? (
        <>
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
                count: activeDocument.word_count,
                unit: activeDocument.word_count === 1 ? t("noun.word") : t("noun.words"),
              })}
            </span>
          </header>
          {saveState === "conflict" ? (
            <div aria-live="assertive" className="editor-conflict" role="alert">
              <strong>{t("editor.conflict.heading")}</strong>
              {error ? <span>{error}</span> : null}
              <div className="editor-conflict__actions">
                <button
                  aria-busy={pendingCommand === "loadLatest" || undefined}
                  disabled={conflictActionsDisabled || onLoadLatest === undefined}
                  onClick={(event) =>
                    runConflictCommand("loadLatest", event.currentTarget, onLoadLatest)
                  }
                  type="button"
                >
                  {t("editor.conflict.action.loadLatest")}
                </button>
                <button
                  aria-busy={pendingCommand === "retryOverwrite" || undefined}
                  disabled={conflictActionsDisabled || onRetryOverwrite === undefined}
                  onClick={(event) =>
                    runConflictCommand("retryOverwrite", event.currentTarget, onRetryOverwrite)
                  }
                  type="button"
                >
                  {t("editor.conflict.action.keepLocal")}
                </button>
              </div>
            </div>
          ) : null}
          <div className="editor__toolbar">
            <span>{t("editor.toolbar.syntax")}</span>
          </div>
          <Suspense fallback={<div className="editor__loading">{t("editor.loading")}</div>}>
            <MarkdownEditor value={draft} onChange={onDraftChange} />
          </Suspense>
        </>
      ) : isLoadingDocument ? (
        <div aria-live="polite" className="editor__empty" role="status">
          <Loader2 aria-hidden="true" className="ui-spin" /> {t("editor.loadingDocument")}
        </div>
      ) : documentLoadError ? (
        <div aria-live="assertive" className="editor__empty" role="alert">
          <strong>{t("editor.error.heading")}</strong>
          <span>{documentLoadError}</span>
          {onRetryDocument ? (
            <button
              className="ui-command ui-command--primary"
              onClick={onRetryDocument}
              type="button"
            >
              {t("editor.action.retryDocument")}
            </button>
          ) : null}
        </div>
      ) : (
        <div className="editor__empty">{t("editor.empty")}</div>
      )}
    </section>
  );
}
