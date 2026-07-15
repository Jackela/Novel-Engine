import { act, useState } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { HttpError, api } from '@/app/api';
import type { Project, Revision, StudioDocument } from '@/app/types/studio';

import { useDocumentDraft } from './useDocumentDraft';

vi.mock('@/app/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/app/api')>();

  return {
    ...actual,
    api: {
      ...actual.api,
      project: vi.fn<typeof actual.api.project>(),
      revisions: vi.fn<typeof actual.api.revisions>(),
      restoreRevision: vi.fn<typeof actual.api.restoreRevision>(),
      saveDocument: vi.fn<typeof actual.api.saveDocument>(),
    },
  };
});

type HookResult = ReturnType<typeof useDocumentDraft>;

interface HarnessResult {
  readonly hook: HookResult;
  readonly project: Project | null;
  readonly error: string | null;
}

const mountedRoots: Array<{ container: HTMLDivElement; root: Root }> = [];

const activeDocument: StudioDocument = {
  id: 'document-1',
  project_id: 'project-1',
  kind: 'chapter',
  title: 'Chapter One',
  position: 0,
  current_revision_id: 'revision-1',
  content_markdown: 'Original draft',
  metadata: {},
  revision_source: 'manual',
  word_count: 2,
  created_at: '2026-06-18T00:00:00Z',
  updated_at: '2026-06-18T00:00:00Z',
};

const initialProject: Project = {
  id: 'project-1',
  title: 'Clockwork Harbor',
  description: 'A harbor of brass clocks.',
  settings: {},
  import_hash: null,
  created_at: '2026-06-18T00:00:00Z',
  updated_at: '2026-06-18T00:00:00Z',
  documents: [activeDocument],
};

const initialRevision: Revision = {
  id: 'revision-1',
  document_id: activeDocument.id,
  parent_revision_id: null,
  revision_number: 1,
  content_markdown: activeDocument.content_markdown,
  metadata: {},
  source: 'manual',
  word_count: 2,
  created_at: '2026-06-18T00:00:00Z',
};

const savedDocument: StudioDocument = {
  ...activeDocument,
  current_revision_id: 'revision-2',
  content_markdown: 'Edited draft',
  word_count: 2,
  updated_at: '2026-06-18T00:01:00Z',
};

const savedRevision: Revision = {
  id: 'revision-2',
  document_id: activeDocument.id,
  parent_revision_id: initialRevision.id,
  revision_number: 2,
  content_markdown: savedDocument.content_markdown,
  metadata: {},
  source: 'manual',
  word_count: 2,
  created_at: '2026-06-18T00:01:00Z',
};

const latestDocument: StudioDocument = {
  ...activeDocument,
  current_revision_id: 'revision-3',
  content_markdown: 'Server latest draft',
  updated_at: '2026-06-18T00:02:00Z',
};

const latestProject: Project = {
  ...initialProject,
  documents: [latestDocument],
  updated_at: latestDocument.updated_at,
};

const overwrittenDocument: StudioDocument = {
  ...latestDocument,
  current_revision_id: 'revision-4',
  content_markdown: 'Conflicting draft',
  updated_at: '2026-06-18T00:03:00Z',
};

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  for (const { container, root } of mountedRoots) {
    act(() => {
      root.unmount();
    });
    container.remove();
  }
  mountedRoots.length = 0;
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.resetAllMocks();
});

function renderDocumentDraftHook(): { readonly result: () => HarnessResult } {
  let current: HarnessResult | undefined;

  function Wrapper(): null {
    const [project, setProject] = useState<Project | null>(initialProject);
    const [error, setError] = useState<string | null>(null);
    const hook = useDocumentDraft(activeDocument, activeDocument.project_id, setProject, setError);
    current = { hook, project, error };
    return null;
  }

  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  mountedRoots.push({ container, root });

  act(() => {
    root.render(<Wrapper />);
  });

  return {
    result: () => {
      if (current === undefined) {
        throw new Error('Expected hook result after render.');
      }
      return current;
    },
  };
}

async function flushMicrotasks(): Promise<void> {
  await act(async () => {
    await Promise.resolve();
  });
}

async function advanceAutosave(): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1500);
  });
}

describe('useDocumentDraft', () => {
  it('initializes drafts and reports a revision loading error as a string', async () => {
    // Given
    vi.mocked(api.revisions).mockRejectedValue(new Error('offline revisions'));

    // When
    const hook = renderDocumentDraftHook();
    await flushMicrotasks();

    // Then
    expect(hook.result().hook.draft).toBe(activeDocument.content_markdown);
    expect(hook.result().hook.titleDraft).toBe(activeDocument.title);
    expect(hook.result().error).toBe('offline revisions');
  });

  it('autosaves an edited draft and exposes the saved project and refreshed revisions', async () => {
    // Given
    vi.mocked(api.revisions)
      .mockResolvedValueOnce({ revisions: [initialRevision] })
      .mockResolvedValueOnce({ revisions: [savedRevision, initialRevision] });
    vi.mocked(api.saveDocument).mockResolvedValue(savedDocument);
    const hook = renderDocumentDraftHook();
    await flushMicrotasks();

    // When
    act(() => {
      hook.result().hook.setDraft(savedDocument.content_markdown);
    });
    await advanceAutosave();
    await advanceAutosave();

    // Then
    expect(api.saveDocument).toHaveBeenCalledWith(activeDocument.project_id, activeDocument.id, {
      content_markdown: savedDocument.content_markdown,
      base_revision_id: activeDocument.current_revision_id,
      title: activeDocument.title,
    });
    expect(api.saveDocument).toHaveBeenCalledTimes(1);
    expect(hook.result().hook.saveState).toBe('saved');
    expect(hook.result().project?.documents).toEqual([savedDocument]);
    expect(hook.result().hook.revisions).toEqual([savedRevision, initialRevision]);
  });

  it('reports a revision conflict when autosave receives an HTTP 409 response', async () => {
    // Given
    vi.mocked(api.revisions).mockResolvedValue({ revisions: [initialRevision] });
    vi.mocked(api.project).mockResolvedValue(latestProject);
    vi.mocked(api.saveDocument).mockRejectedValue(new HttpError('revision conflict', 409));
    const hook = renderDocumentDraftHook();
    await flushMicrotasks();

    // When
    act(() => {
      hook.result().hook.setDraft('Conflicting draft');
    });
    await advanceAutosave();

    // Then
    expect(hook.result().hook.saveState).toBe('conflict');
    expect(hook.result().error).toBe('revision conflict');
    expect(hook.result().hook.draft).toBe('Conflicting draft');
    expect(hook.result().project?.documents).toEqual([latestDocument]);
  });

  it('loads the latest document and discards the local draft after a conflict', async () => {
    // Given
    vi.mocked(api.revisions).mockResolvedValue({ revisions: [initialRevision] });
    vi.mocked(api.project).mockResolvedValue(latestProject);
    vi.mocked(api.saveDocument).mockRejectedValue(new HttpError('revision conflict', 409));
    const hook = renderDocumentDraftHook();
    await flushMicrotasks();
    act(() => {
      hook.result().hook.setDraft('Conflicting draft');
    });
    await advanceAutosave();
    await flushMicrotasks();

    // When
    await act(async () => {
      await hook.result().hook.loadLatest();
    });

    // Then
    expect(api.project).toHaveBeenCalledWith(activeDocument.project_id);
    expect(hook.result().hook.draft).toBe(latestDocument.content_markdown);
    expect(hook.result().hook.titleDraft).toBe(latestDocument.title);
    expect(hook.result().hook.saveState).toBe('idle');
    expect(hook.result().hook.isConflictActionPending).toBe(false);
    expect(hook.result().error).toBeNull();
  });

  it('retries an overwrite against the refreshed revision while keeping the local draft', async () => {
    // Given
    vi.mocked(api.revisions).mockResolvedValue({ revisions: [initialRevision] });
    vi.mocked(api.project).mockResolvedValue(latestProject);
    vi.mocked(api.saveDocument)
      .mockRejectedValueOnce(new HttpError('revision conflict', 409))
      .mockResolvedValueOnce(overwrittenDocument);
    const hook = renderDocumentDraftHook();
    await flushMicrotasks();
    act(() => {
      hook.result().hook.setDraft('Conflicting draft');
    });
    await advanceAutosave();
    await flushMicrotasks();

    // When
    await act(async () => {
      await hook.result().hook.retryOverwrite();
    });

    // Then
    expect(api.saveDocument).toHaveBeenNthCalledWith(
      2,
      activeDocument.project_id,
      activeDocument.id,
      {
        content_markdown: 'Conflicting draft',
        base_revision_id: latestDocument.current_revision_id,
        title: activeDocument.title,
      },
    );
    expect(hook.result().hook.saveState).toBe('saved');
    expect(hook.result().hook.draft).toBe('Conflicting draft');
    expect(hook.result().hook.isConflictActionPending).toBe(false);
    expect(hook.result().error).toBeNull();
  });
});
