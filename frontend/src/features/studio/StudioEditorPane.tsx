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
  onDraftChange: (value: string) => void;
  onTitleChange: (value: string) => void;
}

export function StudioEditorPane({
  activeDocument,
  draft,
  titleDraft,
  saveState,
  onDraftChange,
  onTitleChange,
}: StudioEditorPaneProps) {
  return (
    <section className="studio-editor">
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
              <span className={`save-state save-state--${saveState}`}>
                {saveState === 'saving' ? (
                  <Loader2 className="spin" />
                ) : saveState === 'error' ? (
                  <X />
                ) : (
                  <Check />
                )}
                {saveState === 'idle' ? 'saved' : saveState === 'error' ? 'Save failed' : saveState}
              </span>
            </div>
            <span>{activeDocument.word_count} words</span>
          </header>
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
