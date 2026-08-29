import { act } from 'react';
import { MemoryRouter, useLocation, useNavigationType } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { HttpError, api } from '@/app/api';
import type { Project, Review, StudioExport } from '@/app/types/studio';
import { project, review, studioExport } from '@/test/factories';
import { createMountHarness, flushEffects } from '@/test/harness';

import { useStudioProject } from './useStudioProject';

vi.mock('@/app/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/app/api')>();

  return {
    ...actual,
    api: {
      ...actual.api,
      project: vi.fn<typeof actual.api.project>(),
      reviews: vi.fn<typeof actual.api.reviews>(),
      exports: vi.fn<typeof actual.api.exports>(),
    },
  };
});

type HookResult = ReturnType<typeof useStudioProject>;

interface AggregateFixture {
  readonly project: Project;
  readonly review: Review;
  readonly studioExport: StudioExport;
}

interface HarnessSnapshot {
  readonly hook: HookResult;
  readonly pathname: string;
  readonly navigationType: ReturnType<typeof useNavigationType>;
}

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

function makeAggregate(projectId: string, label: string): AggregateFixture {
  return {
    project: project({
      id: projectId,
      title: `Project ${label}`,
      description: `Description ${label}`,
      settings: { provider: 'mock' },
    }),
    review: review({
      id: `review-${label}`,
      project_id: projectId,
      snapshot_id: `review-snapshot-${label}`,
      model: 'mock-model',
      summary: `Review ${label}`,
    }),
    studioExport: studioExport({
      id: `export-${label}`,
      project_id: projectId,
      snapshot_id: `export-snapshot-${label}`,
      checksum_sha256: `checksum-${label}`,
      download_url: `/downloads/export-${label}`,
    }),
  };
}

function renderStudioProjectHook(
  initialProjectId: string,
  initialPath = `/projects/${initialProjectId}/manuscript`,
): {
  readonly result: () => HarnessSnapshot;
  readonly rerender: (projectId: string) => void;
} {
  let projectId = initialProjectId;
  let current: HarnessSnapshot | undefined;

  function Harness(): null {
    const hook = useStudioProject(projectId);
    const location = useLocation();
    const navigationType = useNavigationType();
    current = { hook, pathname: location.pathname, navigationType };
    return null;
  }

  const { root } = harness.mount(
    <MemoryRouter initialEntries={[initialPath]}>
      <Harness />
    </MemoryRouter>,
  );

  const render = () => {
    root.render(
      <MemoryRouter initialEntries={[initialPath]}>
        <Harness />
      </MemoryRouter>,
    );
  };

  return {
    result: () => {
      if (current === undefined) {
        throw new Error('Expected hook result after render.');
      }
      return current;
    },
    rerender: (nextProjectId: string) => {
      projectId = nextProjectId;
      act(render);
    },
  };
}

describe('useStudioProject', () => {
  it('publishes the complete project aggregate when every request succeeds', async () => {
    // Given
    const fixture = makeAggregate('project-1', 'one');
    vi.mocked(api.project).mockResolvedValue(fixture.project);
    vi.mocked(api.reviews).mockResolvedValue({ reviews: [fixture.review] });
    vi.mocked(api.exports).mockResolvedValue({ exports: [fixture.studioExport] });

    // When
    const harness = renderStudioProjectHook('project-1');
    await flushEffects();

    // Then
    expect(harness.result().hook.project).toEqual(fixture.project);
    expect(harness.result().hook.reviews).toEqual([fixture.review]);
    expect(harness.result().hook.exports).toEqual([fixture.studioExport]);
  });

  it('replaces the route with no partial aggregate when the project is missing (404)', async () => {
    // Given
    const fixture = makeAggregate('project-1', 'one');
    let rejectExports: ((reason?: unknown) => void) | undefined;
    const exportRequest = new Promise<{ exports: StudioExport[] }>((_resolve, reject) => {
      rejectExports = reject;
    });
    vi.mocked(api.project).mockResolvedValue(fixture.project);
    vi.mocked(api.reviews).mockResolvedValue({ reviews: [fixture.review] });
    vi.mocked(api.exports).mockReturnValue(exportRequest);

    // When
    const harness = renderStudioProjectHook('project-1');
    await flushEffects();
    await act(async () => {
      if (rejectExports === undefined) {
        throw new Error('Expected the exports request reject function.');
      }
      rejectExports(new HttpError('Project not found.', 404));
      await exportRequest.catch(() => undefined);
      await Promise.resolve();
    });

    // Then
    expect(harness.result().pathname).toBe('/');
    expect(harness.result().navigationType).toBe('REPLACE');
    expect(harness.result().hook.project).toBeNull();
    expect(harness.result().hook.reviews).toEqual([]);
    expect(harness.result().hook.exports).toEqual([]);
  });

  it('publishes the new aggregate when the project id changes', async () => {
    // Given
    const first = makeAggregate('project-1', 'one');
    const second = makeAggregate('project-2', 'two');
    vi.mocked(api.project)
      .mockResolvedValueOnce(first.project)
      .mockResolvedValueOnce(second.project);
    vi.mocked(api.reviews)
      .mockResolvedValueOnce({ reviews: [first.review] })
      .mockResolvedValueOnce({ reviews: [second.review] });
    vi.mocked(api.exports)
      .mockResolvedValueOnce({ exports: [first.studioExport] })
      .mockResolvedValueOnce({ exports: [second.studioExport] });

    // When
    const harness = renderStudioProjectHook('project-1');
    await flushEffects();
    const firstPublished = harness.result().hook;
    harness.rerender('project-2');
    await flushEffects();

    // Then
    expect(firstPublished.project).toEqual(first.project);
    expect(firstPublished.reviews).toEqual([first.review]);
    expect(firstPublished.exports).toEqual([first.studioExport]);
    expect(harness.result().hook.project).toEqual(second.project);
    expect(harness.result().hook.reviews).toEqual([second.review]);
    expect(harness.result().hook.exports).toEqual([second.studioExport]);
    expect(api.project).toHaveBeenNthCalledWith(1, 'project-1', {
      signal: expect.any(AbortSignal),
    });
    expect(api.project).toHaveBeenNthCalledWith(2, 'project-2', {
      signal: expect.any(AbortSignal),
    });
  });

  it('renders a readable error state and keeps the route when the failure is not a 404', async () => {
    // Given
    vi.mocked(api.project).mockRejectedValue(new HttpError('Upstream failure.', 503));
    vi.mocked(api.reviews).mockResolvedValue({ reviews: [] });
    vi.mocked(api.exports).mockResolvedValue({ exports: [] });

    // When
    const harness = renderStudioProjectHook('project-1');
    await flushEffects();

    // Then: no silent redirect, the error is published for the page to render.
    expect(harness.result().pathname).toBe('/projects/project-1/manuscript');
    expect(harness.result().hook.loadError).toBe('Upstream failure.');
    expect(harness.result().hook.project).toBeNull();
  });

  it('aborts the in-flight requests of the previous project when the id changes', async () => {
    // Given
    const second = makeAggregate('project-2', 'two');
    vi.mocked(api.reviews).mockResolvedValue({ reviews: [] });
    vi.mocked(api.exports).mockResolvedValue({ exports: [] });
    // The stale project request only settles when its signal is aborted.
    vi.mocked(api.project)
      .mockImplementationOnce((_projectId: string, init?: RequestInit) => {
        return new Promise((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () => reject(new Error('Request cancelled.')));
        });
      })
      .mockResolvedValueOnce(second.project);

    // When
    const harness = renderStudioProjectHook('project-1');
    await flushEffects();
    harness.rerender('project-2');
    await flushEffects();

    // Then: the stale call's signal was aborted, the fresh one was not, and
    // the stale response never published project-1 over project-2.
    const [firstProjectCall, secondProjectCall] = vi.mocked(api.project).mock.calls;
    const firstSignal = firstProjectCall?.[1]?.signal ?? null;
    const secondSignal = secondProjectCall?.[1]?.signal ?? null;
    expect(firstSignal?.aborted).toBe(true);
    expect(secondSignal?.aborted).toBe(false);
    expect(harness.result().hook.project).toEqual(second.project);
  });
});
