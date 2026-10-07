import { lazy, Suspense } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";
import type { SaveState, StudioDocument } from "@/app/types/studio";
import { StudioConflictPanel } from "./components/StudioConflictPanel";
import { StudioEditorEmptyState } from "./components/StudioEditorEmptyState";
import { StudioEditorHeader } from "./components/StudioEditorHeader";
import { useConflictCommand } from "./hooks/useConflictCommand";
import type { ServerVersionPreviewController } from "./hooks/useConflictServerPreview";
import { useSaveNowShortcut } from "./hooks/useSaveNowShortcut";

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
  /** DR-029: locate one search hit (term + token) in the opened document. */
  reveal?: { readonly term: string; readonly token: number } | null;
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

export function StudioEditorPane({
  activeDocument,
  draft,
  titleDraft,
  saveState,
  error = null,
  isConflictActionPending = false,
  serverVersion = null,
  reveal = null,
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
  const { conflictActionsDisabled, pendingCommand, runConflictCommand, titleRef } =
    useConflictCommand(saveState, isConflictActionPending);
  // DR-016: Ctrl/Cmd+S must flush the draft instead of opening the browser's
  // save dialog. The listener lives on the window while a Document is open so
  // the shortcut works from the title, the body, and the surrounding chrome.
  useSaveNowShortcut(activeDocument, onSaveNow);

  return (
    <section
      aria-busy={isLoadingDocument || isConflictActionPending || saveState === "saving"}
      className="studio-editor"
    >
      {activeDocument ? (
        <>
          <StudioEditorHeader
            draft={draft}
            onTitleChange={onTitleChange}
            saveState={saveState}
            titleDraft={titleDraft}
            titleRef={titleRef}
            wordCount={activeDocument.word_count}
          />
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
            <MarkdownEditor onChange={onDraftChange} reveal={reveal} value={draft} />
          </Suspense>
        </>
      ) : (
        <StudioEditorEmptyState
          documentLoadError={documentLoadError}
          isLoadingDocument={isLoadingDocument}
          onRetryDocument={onRetryDocument}
        />
      )}
    </section>
  );
}
