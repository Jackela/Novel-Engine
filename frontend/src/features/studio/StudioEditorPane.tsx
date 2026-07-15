import { Check, Loader2, X } from 'lucide-react';
import { lazy, Suspense } from 'react';

import type { SaveState, StudioDocument } from '@/app/types/studio';

const MarkdownEditor = lazy(async () => {
  const module = await import('./MarkdownEditor');
  return { default: module.MarkdownEditor };
});

interface StudioEditorPaneProps {
  activeDocument: StudioDocument | null;
  draft: string;
  titleDraft: string;
  saveState: SaveState;
  error?: string | null;
  isConflictActionPending?: boolean;
  onDraftChange: (value: string) => void;
  onTitleChange: (value: string) => void;
  onLoadLatest?: () => void | Promise<void>;
  onRetryOverwrite?: () => void | Promise<void>;
}

export function StudioEditorPane({
  activeDocument,
  draft,
  titleDraft,
  saveState,
  error = null,
  isConflictActionPending = false,
  onDraftChange,
  onTitleChange,
  onLoadLatest,
  onRetryOverwrite,
}: StudioEditorPaneProps) {
  const saveNeedsAttention = saveState === 'conflict' || saveState === 'error';
  const conflictActionsDisabled = isConflictActionPending || saveState === 'saving';

  return (
    <section
      aria-busy={isConflictActionPending || saveState === 'saving'}
      className="studio-editor"
    >
      {activeDocument ? (
        <>
          <header className="editor-header">
            <div>
              <input
                aria-label="Document title"
                className="editor-title"
                value={titleDraft}
                onChange={(event) => onTitleChange(event.target.value)}
              />
              <span
                aria-atomic="true"
                aria-live={saveNeedsAttention ? 'assertive' : 'polite'}
                className={`save-state save-state--${saveState}`}
                role={saveNeedsAttention ? 'alert' : 'status'}
              >
                {saveState === 'saving' ? (
                  <Loader2 aria-hidden="true" className="spin" />
                ) : saveNeedsAttention ? (
                  <X aria-hidden="true" />
                ) : (
                  <Check aria-hidden="true" />
                )}
                {saveState === 'idle' || saveState === 'saved'
                  ? 'Saved'
                  : saveState === 'saving'
                    ? 'saving'
                    : saveState === 'conflict'
                      ? 'Save conflict'
                      : 'Save failed'}
              </span>
            </div>
            <span className="editor-word-count">{activeDocument.word_count} words</span>
          </header>
          {saveState === 'conflict' ? (
            <div aria-live="assertive" className="editor-conflict" role="alert">
              <strong>Someone else changed this document.</strong>
              {error ? <span>{error}</span> : null}
              <div className="editor-conflict__actions">
                <button
                  disabled={conflictActionsDisabled || onLoadLatest === undefined}
                  onClick={() => void onLoadLatest?.()}
                  type="button"
                >
                  Load latest (discard local)
                </button>
                <button
                  disabled={conflictActionsDisabled || onRetryOverwrite === undefined}
                  onClick={() => void onRetryOverwrite?.()}
                  type="button"
                >
                  Keep local and retry overwrite
                </button>
              </div>
            </div>
          ) : null}
          <div className="editor-toolbar">
            <span>Markdown</span>
          </div>
          <Suspense fallback={<div className="editor-loading">Loading editor...</div>}>
            <MarkdownEditor value={draft} onChange={onDraftChange} />
          </Suspense>
        </>
      ) : (
        <div className="empty-editor">Create a document to begin writing.</div>
      )}
    </section>
  );
}
