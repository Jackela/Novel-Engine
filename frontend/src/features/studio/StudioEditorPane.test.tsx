import { fireEvent } from '@testing-library/dom';
import { act, type ReactElement } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { StudioDocument } from '@/app/types/studio';

import { StudioEditorPane } from './StudioEditorPane';

vi.mock('./MarkdownEditor', () => ({
  MarkdownEditor: ({ value, onChange }: { value: string; onChange: (value: string) => void }) => (
    <textarea
      aria-label="Markdown body"
      onChange={(event) => onChange(event.target.value)}
      value={value}
    />
  ),
}));

const mountedRoots: Array<{ container: HTMLDivElement; root: Root }> = [];

function render(element: ReactElement): HTMLDivElement {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => {
    root.render(element);
  });
  mountedRoots.push({ container, root });
  return container;
}

afterEach(() => {
  for (const { container, root } of mountedRoots) {
    act(() => {
      root.unmount();
    });
    container.remove();
  }
  mountedRoots.length = 0;
});

const baseDocument: StudioDocument = {
  id: 'doc-1',
  project_id: 'project-1',
  kind: 'chapter',
  title: 'Opening',
  position: 1,
  current_revision_id: 'revision-abcdefghi',
  content_markdown: '# Opening',
  metadata: {},
  revision_source: 'author',
  word_count: 42,
  created_at: '2026-06-16T00:00:00Z',
  updated_at: '2026-06-16T00:00:00Z',
};

describe('Studio editor pane', () => {
  it('renders editor state and forwards title/body edits', async () => {
    const onTitleChange = vi.fn();
    const onDraftChange = vi.fn();
    const container = render(
      <StudioEditorPane
        activeDocument={baseDocument}
        draft="# Opening"
        titleDraft="Opening"
        saveState="saving"
        onDraftChange={onDraftChange}
        onTitleChange={onTitleChange}
      />,
    );

    await act(async () => {
      await Promise.resolve();
    });

    const title = container.querySelector('input[aria-label="Document title"]');
    const body = container.querySelector('textarea[aria-label="Markdown body"]');
    expect(container.textContent).toContain('42 words');
    expect(container.textContent).toContain('saving');

    act(() => {
      if (title instanceof HTMLInputElement) {
        fireEvent.input(title, { target: { value: 'New Opening' } });
      }
      if (body instanceof HTMLTextAreaElement) {
        fireEvent.input(body, { target: { value: '# New Opening' } });
      }
    });

    expect(onTitleChange).toHaveBeenCalledWith('New Opening');
    expect(onDraftChange).toHaveBeenCalledWith('# New Opening');
  });

  it('renders a successful save status without the failure label', () => {
    const container = render(
      <StudioEditorPane
        activeDocument={baseDocument}
        draft="# Opening"
        titleDraft="Opening"
        saveState="saved"
        onDraftChange={vi.fn()}
        onTitleChange={vi.fn()}
      />,
    );

    const saveStatus = container.querySelector('.save-state');
    expect(saveStatus?.textContent).toContain('Saved');
    expect(saveStatus?.textContent).not.toContain('Save failed');
  });
});
