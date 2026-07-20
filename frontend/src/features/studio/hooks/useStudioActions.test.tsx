import { act, useState } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/app/api';
import type { Project, Review, StudioDocument, StudioJob } from '@/app/types/studio';
import type { InspectorTab } from '@/features/studio/studioConstants';

import { useStudioActions } from './useStudioActions';

vi.mock('@/app/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/app/api')>();
  return {
    ...actual,
    api: {
      ...actual.api,
      createDocument: vi.fn<typeof actual.api.createDocument>(),
      reorderDocuments: vi.fn<typeof actual.api.reorderDocuments>(),
      createReview: vi.fn<typeof actual.api.createReview>(),
      updateProject: vi.fn<typeof actual.api.updateProject>(),
      retryJob: vi.fn<typeof actual.api.retryJob>(),
    },
  };
});

interface HarnessSnapshot {
  readonly actions: ReturnType<typeof useStudioActions>;
  readonly project: Project | null;
  readonly reviews: Review[];
  readonly error: string | null;
  readonly activeId: string | null;
  readonly inspector: InspectorTab;
}

const chapter: StudioDocument = {
  id: 'chapter-1',
  project_id: 'project-1',
  kind: 'chapter',
  title: 'Chapter One',
  position: 0,
  current_revision_id: 'revision-1',
  content_markdown: '# Chapter 1\n\n',
  metadata: {},
  revision_source: 'manual',
  word_count: 2,
  created_at: '2026-06-20T00:00:00Z',
  updated_at: '2026-06-20T00:00:00Z',
};
const note: StudioDocument = {
  ...chapter,
  id: 'note-1',
  kind: 'note',
  title: 'Note One',
  position: 1,
  content_markdown: '',
};
const projectFixture: Project = {
  id: 'project-1',
  title: 'Clockwork Harbor',
  description: 'Old description',
  settings: { provider: 'mock', temperature: 0.5 },
  import_hash: null,
  created_at: '2026-06-20T00:00:00Z',
  updated_at: '2026-06-20T00:00:00Z',
  documents: [chapter, note],
};
const review: Review = {
  id: 'review-1',
  project_id: projectFixture.id,
  snapshot_id: 'snapshot-1',
  provider: 'mock',
  model: 'studio-copilot-v1',
  summary: 'Looks good.',
  created_at: '2026-06-20T00:01:00Z',
  issues: [],
};
const retriedJob: StudioJob = {
  id: 'job-1',
  project_id: projectFixture.id,
  document_id: chapter.id,
  kind: 'proposal',
  operation: 'continue',
  status: 'pending',
  provider: 'mock',
  model: 'studio-copilot-v1',
  request: {},
  result: {},
  error: null,
  retry_of_job_id: 'failed-job-1',
  events: [],
  created_at: '2026-06-20T00:02:00Z',
  updated_at: '2026-06-20T00:02:00Z',
};
const mountedRoots: Array<{ container: HTMLDivElement; root: Root }> = [];

afterEach(() => {
  for (const { container, root } of mountedRoots) {
    act(() => {
      root.unmount();
    });
    container.remove();
  }
  mountedRoots.length = 0;
  vi.resetAllMocks();
});

function renderActions(
  loadJobs: ReturnType<typeof vi.fn<() => Promise<void>>> = vi
    .fn<() => Promise<void>>()
    .mockResolvedValue(undefined),
): {
  readonly result: () => HarnessSnapshot;
  readonly loadJobs: ReturnType<typeof vi.fn<() => Promise<void>>>;
  readonly submitSettings: () => void;
} {
  let current: HarnessSnapshot | undefined;

  function Wrapper() {
    const [project, setProject] = useState<Project | null>(projectFixture);
    const [reviews, setReviews] = useState<Review[]>([]);
    const [error, setError] = useState<string | null>('previous error');
    const [activeId, setActiveId] = useState<string | null>(null);
    const [inspector, setInspector] = useState<InspectorTab>('history');
    const actions = useStudioActions({
      project,
      projectId: projectFixture.id,
      setProject,
      setReviews,
      setError,
      setActiveId,
      setInspector,
      settingsForm: {
        title: 'Updated Harbor',
        description: 'Updated description',
        provider: 'dashscope',
      },
      loadJobs,
    });
    current = { actions, project, reviews, error, activeId, inspector };
    return <form onSubmit={actions.updateProjectSettings} />;
  }

  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  mountedRoots.push({ container, root });
  act(() => {
    root.render(<Wrapper />);
  });
  const form = container.querySelector('form');
  if (form === null) {
    throw new Error('Expected settings form after render.');
  }

  return {
    result: () => {
      if (current === undefined) {
        throw new Error('Expected actions hook result after render.');
      }
      return current;
    },
    loadJobs,
    submitSettings: () => {
      form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    },
  };
}

describe('useStudioActions', () => {
  it('creates a numbered chapter, appends it, and activates it', async () => {
    // Given
    const created = { ...chapter, id: 'chapter-2', title: 'Chapter 2', position: 2 };
    vi.mocked(api.createDocument).mockResolvedValue(created);
    const harness = renderActions();

    // When
    await act(async () => {
      await harness.result().actions.createDocument('chapter');
    });

    // Then
    expect(api.createDocument).toHaveBeenCalledWith(projectFixture.id, {
      kind: 'chapter',
      title: 'Chapter 2',
      content_markdown: '# Chapter 2\n\n',
    });
    expect(harness.result().project?.documents).toEqual([chapter, note, created]);
    expect(harness.result().activeId).toBe(created.id);
  });

  it('reorders documents and publishes the server ordering', async () => {
    // Given
    const reordered = [
      { ...note, position: 0 },
      { ...chapter, position: 1 },
    ];
    vi.mocked(api.reorderDocuments).mockResolvedValue({ documents: reordered });
    const harness = renderActions();

    // When
    await act(async () => {
      await harness.result().actions.moveDocument(note.id, -1);
    });

    // Then
    expect(api.reorderDocuments).toHaveBeenCalledWith(projectFixture.id, [note.id, chapter.id]);
    expect(harness.result().project?.documents).toEqual(reordered);
  });

  it('runs a review and opens the review inspector', async () => {
    // Given
    vi.mocked(api.createReview).mockResolvedValue(review);
    const harness = renderActions();

    // When
    await act(async () => {
      await harness.result().actions.runReview();
    });

    // Then
    expect(harness.result().reviews).toEqual([review]);
    expect(harness.result().inspector).toBe('review');
  });

  it('updates settings while preserving unrelated project settings', async () => {
    // Given
    const updated = {
      ...projectFixture,
      title: 'Updated Harbor',
      description: 'Updated description',
      settings: { provider: 'dashscope', temperature: 0.5 },
    };
    vi.mocked(api.updateProject).mockResolvedValue(updated);
    const harness = renderActions();

    // When
    await act(async () => {
      harness.submitSettings();
    });

    // Then
    expect(api.updateProject).toHaveBeenCalledWith(projectFixture.id, {
      title: 'Updated Harbor',
      description: 'Updated description',
      settings: { provider: 'dashscope', temperature: 0.5 },
    });
    expect(harness.result().project).toEqual(updated);
    expect(harness.result().error).toBeNull();
  });

  it('reloads jobs after retrying a failed job', async () => {
    // Given
    let resolveLoadJobs: (() => void) | undefined;
    const loadJobs = vi.fn<() => Promise<void>>().mockReturnValue(
      new Promise<void>((resolve) => {
        resolveLoadJobs = resolve;
      }),
    );
    let resolveRetry: ((job: StudioJob) => void) | undefined;
    vi.mocked(api.retryJob).mockReturnValue(
      new Promise<StudioJob>((resolve) => {
        resolveRetry = resolve;
      }),
    );
    const harness = renderActions(loadJobs);

    // When
    const retryPromise = harness.result().actions.retryJob('job-1');
    await act(async () => {
      await Promise.resolve();
    });

    // Then
    expect(api.retryJob).toHaveBeenCalledWith(projectFixture.id, 'job-1');
    expect(harness.result().actions.retryingJobId).toBe('job-1');

    await act(async () => {
      resolveRetry?.(retriedJob);
      await Promise.resolve();
    });

    expect(harness.loadJobs).toHaveBeenCalledTimes(1);
    expect(harness.result().actions.retryingJobId).toBe('job-1');

    await act(async () => {
      resolveLoadJobs?.();
      await retryPromise;
    });

    expect(harness.result().actions.retryingJobId).toBeNull();
  });
});
