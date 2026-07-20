import { act, useState } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/app/api';
import type { Project, Revision, StudioDocument } from '@/app/types/studio';

import { useDocumentDraft } from './useDocumentDraft';
import { useRevisionCache } from './useRevisionCache';

vi.mock('@/app/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/app/api')>();
  return {
    ...actual,
    api: {
      ...actual.api,
      revisions: vi.fn<typeof actual.api.revisions>(),
      restoreRevision: vi.fn<typeof actual.api.restoreRevision>(),
    },
  };
});

type HookResult = ReturnType<typeof useRevisionCache>;
type DraftHookResult = ReturnType<typeof useDocumentDraft>;

const mountedRoots: Array<{ container: HTMLDivElement; root: Root }> = [];

afterEach(() => {
  for (const { container, root } of mountedRoots) {
    act(() => root.unmount());
    container.remove();
  }
  mountedRoots.length = 0;
  vi.resetAllMocks();
});

const revision: Revision = {
  id: 'revision-1',
  document_id: 'document-1',
  parent_revision_id: null,
  revision_number: 1,
  content_markdown: 'Draft',
  metadata: {},
  source: 'manual',
  word_count: 1,
  created_at: '2026-07-20T00:00:00Z',
};

const staleRevision: Revision = {
  ...revision,
  id: 'revision-stale',
  content_markdown: 'Stale draft',
};

const activeDocument: StudioDocument = {
  id: 'document-1',
  project_id: 'project-1',
  kind: 'chapter',
  title: 'Chapter One',
  position: 0,
  current_revision_id: 'revision-current',
  content_markdown: 'Draft',
  metadata: {},
  revision_source: 'manual',
  word_count: 1,
  created_at: '2026-07-20T00:00:00Z',
  updated_at: '2026-07-20T00:00:00Z',
};

const project: Project = {
  id: 'project-1',
  title: 'Novel',
  description: '',
  settings: {},
  import_hash: null,
  created_at: '2026-07-20T00:00:00Z',
  updated_at: '2026-07-20T00:00:00Z',
  documents: [activeDocument],
};

const restoredDocument: StudioDocument = {
  ...activeDocument,
  current_revision_id: 'revision-restored',
  content_markdown: 'Restored draft',
  updated_at: '2026-07-20T00:01:00Z',
};

function renderCache(): {
  readonly result: () => { readonly hook: HookResult };
  readonly dispose: () => void;
} {
  let current: { readonly hook: HookResult } | undefined;
  const onError = vi.fn();

  function Wrapper(): null {
    current = { hook: useRevisionCache('project-1', 'document-1', onError) };
    return null;
  }

  const container = document.createElement('div');
  const root = createRoot(container);
  act(() => root.render(<Wrapper />));
  document.body.appendChild(container);
  mountedRoots.push({ container, root });

  return {
    result: () => {
      if (current === undefined) throw new Error('Expected hook result after render.');
      return current;
    },
    dispose: () => {
      act(() => root.unmount());
      container.remove();
      const index = mountedRoots.findIndex((mounted) => mounted.root === root);
      if (index >= 0) mountedRoots.splice(index, 1);
    },
  };
}

function renderDraft(): { readonly result: () => { readonly hook: DraftHookResult } } {
  let current: { readonly hook: DraftHookResult } | undefined;

  function Wrapper(): null {
    const [, setProject] = useState<Project | null>(project);
    const [, setError] = useState<string | null>(null);
    current = {
      hook: useDocumentDraft(activeDocument, 'project-1', setProject, setError),
    };
    return null;
  }

  const container = document.createElement('div');
  const root = createRoot(container);
  act(() => root.render(<Wrapper />));
  document.body.appendChild(container);
  mountedRoots.push({ container, root });

  return {
    result: () => {
      if (current === undefined) throw new Error('Expected hook result after render.');
      return current;
    },
  };
}

describe('useRevisionCache', () => {
  it('resolves refresh after the latest revision response updates the cache', async () => {
    let resolveResponse: ((response: { revisions: Revision[] }) => void) | undefined;
    vi.mocked(api.revisions)
      .mockResolvedValueOnce({ revisions: [] })
      .mockReturnValueOnce(
        new Promise((resolve) => {
          resolveResponse = resolve;
        }),
      );
    const cache = renderCache();

    let settled = false;
    const refresh = cache.result().hook.refreshDocumentRevisions('document-1');
    refresh.then(() => {
      settled = true;
    });

    await act(async () => {
      await Promise.resolve();
    });
    expect(settled).toBe(false);

    await act(async () => {
      resolveResponse?.({ revisions: [revision] });
      await refresh;
      await Promise.resolve();
    });

    expect(settled).toBe(true);
    expect(cache.result().hook.revisions).toEqual([revision]);
  });

  it('does not let an unmounted cache instance overwrite a newer response', async () => {
    let resolveStale: ((response: { revisions: Revision[] }) => void) | undefined;
    let resolveCurrent: ((response: { revisions: Revision[] }) => void) | undefined;
    vi.mocked(api.revisions)
      .mockReturnValueOnce(
        new Promise((resolve) => {
          resolveStale = resolve;
        }),
      )
      .mockReturnValueOnce(
        new Promise((resolve) => {
          resolveCurrent = resolve;
        }),
      );

    const staleCache = renderCache();
    staleCache.dispose();
    const currentCache = renderCache();

    await act(async () => {
      resolveCurrent?.({ revisions: [revision] });
      await Promise.resolve();
    });
    await act(async () => {
      resolveStale?.({ revisions: [staleRevision] });
      await Promise.resolve();
    });

    expect(currentCache.result().hook.revisions).toEqual([revision]);
  });

  it('keeps restore pending until the revision refresh completes', async () => {
    let resolveRefresh: ((response: { revisions: Revision[] }) => void) | undefined;
    vi.mocked(api.revisions)
      .mockResolvedValueOnce({ revisions: [] })
      .mockReturnValueOnce(
        new Promise((resolve) => {
          resolveRefresh = resolve;
        }),
      );
    vi.mocked(api.restoreRevision).mockResolvedValue(restoredDocument);
    const draft = renderDraft();

    let settled = false;
    const restore = draft.result().hook.restoreRevision('revision-old');
    restore.then(() => {
      settled = true;
    });

    await act(async () => {
      await Promise.resolve();
    });
    expect(api.restoreRevision).toHaveBeenCalledWith(
      'project-1',
      activeDocument.id,
      'revision-old',
      activeDocument.current_revision_id,
    );
    expect(settled).toBe(false);

    await act(async () => {
      resolveRefresh?.({ revisions: [revision] });
      await restore;
      await Promise.resolve();
    });

    expect(settled).toBe(true);
  });
});
