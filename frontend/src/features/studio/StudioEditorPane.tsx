import { Check, Loader2, X } from "lucide-react";
import { lazy, Suspense, useRef, useState } from "react";

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
  const titleRef = useRef<HTMLInputElement>(null);
  const pendingCommandRef = useRef<"loadLatest" | "retryOverwrite" | null>(null);
  const [pendingCommand, setPendingCommand] = useState<"loadLatest" | "retryOverwrite" | null>(
    null,
  );
  const saveNeedsAttention = saveState === "conflict" || saveState === "error";
  const conflictActionsDisabled =
    pendingCommand !== null || isConflictActionPending || saveState === "saving";
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
                aria-label="Document title"
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
                {saveState === "idle" || saveState === "saved"
                  ? "Saved"
                  : saveState === "saving"
                    ? "saving"
                    : saveState === "conflict"
                      ? "Save conflict"
                      : "Save failed"}
              </span>
            </div>
            <span className="editor-word-count">{activeDocument.word_count} words</span>
          </header>
          {saveState === "conflict" ? (
            <div aria-live="assertive" className="editor-conflict" role="alert">
              <strong>Someone else changed this document.</strong>
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
                  Load latest (discard local)
                </button>
                <button
                  aria-busy={pendingCommand === "retryOverwrite" || undefined}
                  disabled={conflictActionsDisabled || onRetryOverwrite === undefined}
                  onClick={(event) =>
                    runConflictCommand("retryOverwrite", event.currentTarget, onRetryOverwrite)
                  }
                  type="button"
                >
                  Keep local and retry overwrite
                </button>
              </div>
            </div>
          ) : null}
          <div className="editor__toolbar">
            <span>Markdown</span>
          </div>
          <Suspense fallback={<div className="editor__loading">Loading editor...</div>}>
            <MarkdownEditor value={draft} onChange={onDraftChange} />
          </Suspense>
        </>
      ) : isLoadingDocument ? (
        <div aria-live="polite" className="editor__empty" role="status">
          <Loader2 aria-hidden="true" className="ui-spin" /> Loading document
        </div>
      ) : documentLoadError ? (
        <div aria-live="assertive" className="editor__empty" role="alert">
          <strong>Unable to open this document</strong>
          <span>{documentLoadError}</span>
          {onRetryDocument ? (
            <button
              className="ui-command ui-command--primary"
              onClick={onRetryDocument}
              type="button"
            >
              Retry document
            </button>
          ) : null}
        </div>
      ) : (
        <div className="editor__empty">Create a document to begin writing.</div>
      )}
    </section>
  );
}
