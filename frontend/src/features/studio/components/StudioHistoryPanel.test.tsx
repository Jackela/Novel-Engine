import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Revision } from '@/app/types/studio';

import { StudioHistoryPanel } from './StudioHistoryPanel';

const mountedRoots: Array<{ container: HTMLDivElement; root: Root }> = [];

afterEach(() => {
  for (const { container, root } of mountedRoots) {
    act(() => root.unmount());
    container.remove();
  }
  mountedRoots.length = 0;
});

const revisions: Revision[] = [
  {
    id: 'revision-old',
    document_id: 'document-1',
    parent_revision_id: null,
    revision_number: 1,
    content_markdown: 'Old draft',
    metadata: {},
    source: 'manual',
    word_count: 2,
    created_at: '2026-06-16T00:00:00Z',
  },
  {
    id: 'revision-other',
    document_id: 'document-1',
    parent_revision_id: 'revision-old',
    revision_number: 2,
    content_markdown: 'Other draft',
    metadata: {},
    source: 'manual',
    word_count: 2,
    created_at: '2026-06-16T00:01:00Z',
  },
  {
    id: 'revision-current',
    document_id: 'document-1',
    parent_revision_id: 'revision-other',
    revision_number: 3,
    content_markdown: 'Current draft',
    metadata: {},
    source: 'manual',
    word_count: 2,
    created_at: '2026-06-16T00:02:00Z',
  },
];

function renderHistory(restoringRevisionId: string | null): HTMLDivElement {
  const container = document.createElement('div');
  const root = createRoot(container);
  act(() => {
    root.render(
      <StudioHistoryPanel
        revisions={revisions}
        loadedRevisionId="revision-current"
        onRestoreRevision={vi.fn()}
        restoringRevisionId={restoringRevisionId}
      />,
    );
  });
  document.body.appendChild(container);
  mountedRoots.push({ container, root });
  return container;
}

describe('StudioHistoryPanel', () => {
  it('locks every restore action while one revision is restoring', () => {
    const container = renderHistory('revision-old');
    const restoreButtons = Array.from(
      container.querySelectorAll<HTMLButtonElement>('.icon-command'),
    );

    expect(container.querySelector('.inspector-content')?.getAttribute('aria-busy')).toBe('true');
    expect(restoreButtons).toHaveLength(2);
    expect(restoreButtons.every((button) => button.disabled)).toBe(true);
    expect(restoreButtons[0]?.getAttribute('aria-busy')).toBe('true');
    expect(restoreButtons[0]?.getAttribute('aria-label')).toBe('Restoring revision revision');
    expect(restoreButtons[1]?.getAttribute('aria-label')).toBe('Restore revision revision');
  });

  it('keeps restore actions available when no revision is restoring', () => {
    const container = renderHistory(null);
    const restoreButtons = Array.from(
      container.querySelectorAll<HTMLButtonElement>('.icon-command'),
    );

    expect(restoreButtons.every((button) => !button.disabled)).toBe(true);
    expect(container.querySelector('.inspector-content')?.getAttribute('aria-busy')).toBe('false');
  });
});
