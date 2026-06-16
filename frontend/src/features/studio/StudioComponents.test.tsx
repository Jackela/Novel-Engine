import { fireEvent } from '@testing-library/dom';
import { act, type FormEvent, type ReactElement } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Project, Session, StudioDocument } from '@/app/types/studio';

import { StudioEditorPane } from './StudioEditorPane';
import { StudioNavigator } from './StudioNavigator';
import { StudioTopbar } from './StudioTopbar';

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

function click(element: Element | null): void {
  if (!(element instanceof HTMLElement)) {
    throw new Error('Expected a clickable element.');
  }
  act(() => {
    element.click();
  });
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

const secondDocument: StudioDocument = {
  ...baseDocument,
  id: 'doc-2',
  title: 'Second',
  position: 2,
  current_revision_id: 'revision-second',
  word_count: 12,
};

const baseProject: Project = {
  id: 'project-1',
  title: 'Clockwork Harbor',
  description: '',
  settings: {},
  import_hash: null,
  created_at: '2026-06-16T00:00:00Z',
  updated_at: '2026-06-16T00:00:00Z',
  documents: [baseDocument, secondDocument],
};

describe('Studio split components', () => {
  it('routes topbar actions without owning page state', () => {
    const callbacks = {
      back: vi.fn(),
      review: vi.fn(),
      exportProject: vi.fn(),
      settings: vi.fn(),
    };
    const guestSession: Session = {
      session_id: 'session-1',
      kind: 'guest',
      owner_id: null,
      expires_at: '2026-06-16T12:00:00Z',
    };

    const container = render(
      <StudioTopbar
        project={baseProject}
        session={guestSession}
        onBack={callbacks.back}
        onReview={callbacks.review}
        onExport={callbacks.exportProject}
        onSettings={callbacks.settings}
      />,
    );

    expect(container.textContent).toContain('Clockwork Harbor');
    click(container.querySelector('button[title="Projects"]'));
    click(container.querySelector('.command:not(.command--primary)'));
    click(container.querySelector('button[title="Project settings"]'));
    click(Array.from(container.querySelectorAll('.export-menu__items button'))[1]);

    expect(callbacks.back).toHaveBeenCalledTimes(1);
    expect(callbacks.review).toHaveBeenCalledTimes(1);
    expect(callbacks.settings).toHaveBeenCalledTimes(1);
    expect(callbacks.exportProject).toHaveBeenCalledWith('docx');
  });

  it('keeps navigation callbacks scoped to section, search, and document actions', () => {
    const callbacks = {
      searchChange: vi.fn(),
      searchSubmit: vi.fn((event: FormEvent) => event.preventDefault()),
      navigateSection: vi.fn(),
      selectDocument: vi.fn(),
      createDocument: vi.fn(),
      moveDocument: vi.fn(),
    };

    const container = render(
      <StudioNavigator
        project={baseProject}
        section="manuscript"
        activeId="doc-1"
        search="harbor"
        isSearching={false}
        searchResults={[{ document_id: 'doc-1', title: 'Opening', excerpt: 'Harbor' }]}
        onSearchChange={callbacks.searchChange}
        onSearchSubmit={callbacks.searchSubmit}
        onNavigateSection={callbacks.navigateSection}
        onSelectDocument={callbacks.selectDocument}
        onCreateDocument={callbacks.createDocument}
        onMoveDocument={callbacks.moveDocument}
      />,
    );

    click(Array.from(container.querySelectorAll('.section-nav button'))[1]);
    click(container.querySelector('.search-results button'));
    click(container.querySelector('.document-group header button'));
    click(container.querySelector('.document-order button:last-child'));
    act(() => {
      container.querySelector('form')?.dispatchEvent(new Event('submit', { bubbles: true }));
    });

    expect(callbacks.navigateSection).toHaveBeenCalledWith('outline');
    expect(callbacks.selectDocument).toHaveBeenCalledWith('doc-1');
    expect(callbacks.createDocument).toHaveBeenCalledWith('chapter');
    expect(callbacks.moveDocument).toHaveBeenCalledWith('doc-1', 1);
    expect(callbacks.searchSubmit).toHaveBeenCalledTimes(1);
  });

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
});
