import { Check, Loader2, X } from "lucide-react";
import { lazy, Suspense, useEffect, useRef, useState } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";
import type { SaveState, StudioDocument } from "@/app/types/studio";
import { StudioConflictPanel } from "./components/StudioConflictPanel";
import { useCommandFocusRestoration } from "./hooks/useCommandFocusRestoration";
import type { ServerVersionPreviewController } from "./hooks/useConflictServerPreview";

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
  /** DR-012: the conflict panel's read-only server-version preview controller. */
  serverVersion?: ServerVersionPreviewController | null;
  isLoadingDocument?: boolean;
  documentLoadError?: string | null;
  onDraftChange: (value: string) => void;
  onTitleChange: (value: string) => void;
  onLoadLatest?: () => void | Promise<void>;
  onRetryOverwrite?: () => void | Promise<void>;
  onRetrySave?: () => void | Promise<void>;
  /** DR-016: immediate draft flush for the Ctrl/Cmd+S shortcut. */
  onSaveNow?: () => void;
  onRetryDocument?: () => void;
}

type EditorCommand = "loadLatest" | "retryOverwrite" | "retrySave";

export function StudioEditorPane({
  activeDocument,
  draft,
  titleDraft,
  saveState,
  error = null,
  isConflictActionPending = false,
  serverVersion = null,
  isLoadingDocument = false,
  documentLoadError = null,
  onDraftChange,
  onTitleChange,
  onLoadLatest,
  onRetryOverwrite,
  onRetrySave,
  onSaveNow,
  onRetryDocument,
}: StudioEditorPaneProps) {
  const { t } = useTranslation();
  const titleRef = useRef<HTMLInputElement>(null);
  const pendingCommandRef = useRef<EditorCommand | null>(null);
  const [pendingCommand, setPendingCommand] = useState<EditorCommand | null>(null);
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

  // DR-016: Ctrl/Cmd+S must flush the draft instead of opening the browser's
  // save dialog. The listener lives on the window while a Document is open so
  // the shortcut works from the title, the body, and the surrounding chrome.
  useEffect(() => {
    if (!activeDocument || !onSaveNow) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (!(event.ctrlKey || event.metaKey) || event.altKey || event.shiftKey) return;
      if (event.key.toLowerCase() !== "s") return;
      event.preventDefault();
      onSaveNow();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [activeDocument, onSaveNow]);

  const runConflictCommand = (
    commandKey: EditorCommand,
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
            <StudioConflictPanel
              disabled={conflictActionsDisabled}
              error={error}
              onLoadLatest={onLoadLatest}
              onRetryOverwrite={onRetryOverwrite}
              onRunCommand={runConflictCommand}
              pendingCommand={pendingCommand}
              serverVersion={serverVersion}
            />
          ) : null}
          {saveState === "error" ? (
            <div aria-live="assertive" className="editor-conflict" role="alert">
              <strong>{t("editor.saveState.error")}</strong>
              {error ? <span>{error}</span> : null}
              <div className="editor-conflict__actions">
                <button
                  aria-busy={pendingCommand === "retrySave" || undefined}
                  disabled={conflictActionsDisabled || onRetrySave === undefined}
                  onClick={(event) =>
                    runConflictCommand("retrySave", event.currentTarget, onRetrySave)
                  }
                  type="button"
                >
                  {t("editor.action.retrySave")}
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
