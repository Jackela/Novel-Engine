import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { MemoryRouter, useLocation, useNavigationType } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/app/api';
import type { Project, Review, Session, StudioExport } from '@/app/types/studio';

import { useStudioProject } from './useStudioProject';

vi.mock('@/app/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/app/api')>();

  return {
    ...actual,
    api: {
      ...actual.api,
      session: vi.fn<typeof actual.api.session>(),
      project: vi.fn<typeof actual.api.project>(),
      reviews: vi.fn<typeof actual.api.reviews>(),
      exports: vi.fn<typeof actual.api.exports>(),
    },
  };
});

type HookResult = ReturnType<typeof useStudioProject>;

interface AggregateFixture {
  readonly session: Session;
  readonly project: Project;
  readonly review: Review;
  readonly studioExport: StudioExport;
}

interface HarnessSnapshot {
  readonly hook: HookResult;
  readonly pathname: string;
  readonly navigationType: ReturnType<typeof useNavigationType>;
}

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

function makeAggregate(projectId: string, label: string): AggregateFixture {
  return {
    session: {
      session_id: `session-${label}`,
      kind: 'owner',
      owner_id: `owner-${label}`,
      expires_at: null,
    },
    project: {
      id: projectId,
      title: `Project ${label}`,
      description: `Description ${label}`,
      settings: { provider: 'mock' },
      import_hash: null,
      created_at: '2026-06-18T00:00:00Z',
      updated_at: '2026-06-18T00:00:00Z',
      documents: [],
    },
    review: {
      id: `review-${label}`,
      project_id: projectId,
      snapshot_id: `review-snapshot-${label}`,
      provider: 'mock',
      model: 'mock-model',
      summary: `Review ${label}`,
      created_at: '2026-06-18T00:01:00Z',
      issues: [],
    },
    studioExport: {
      id: `export-${label}`,
      project_id: projectId,
      snapshot_id: `export-snapshot-${label}`,
      format: 'markdown',
      size_bytes: 128,
      checksum_sha256: `checksum-${label}`,
      created_at: '2026-06-18T00:02:00Z',
      download_url: `/downloads/export-${label}`,
    },
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

  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  mountedRoots.push({ container, root });

  const render = () => {
    root.render(
      <MemoryRouter initialEntries={[initialPath]}>
        <Harness />
      </MemoryRouter>,
    );
  };

  act(render);

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

async function flushEffects(): Promise<void> {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

describe('useStudioProject', () => {
  it('publishes the complete project aggregate when every request succeeds', async () => {
    // Given
    const fixture = makeAggregate('project-1', 'one');
    vi.mocked(api.session).mockResolvedValue(fixture.session);
    vi.mocked(api.project).mockResolvedValue(fixture.project);
    vi.mocked(api.reviews).mockResolvedValue({ reviews: [fixture.review] });
    vi.mocked(api.exports).mockResolvedValue({ exports: [fixture.studioExport] });

    // When
    const harness = renderStudioProjectHook('project-1');
    await flushEffects();

    // Then
    expect(harness.result().hook.session).toEqual(fixture.session);
    expect(harness.result().hook.project).toEqual(fixture.project);
    expect(harness.result().hook.reviews).toEqual([fixture.review]);
    expect(harness.result().hook.exports).toEqual([fixture.studioExport]);
  });

  it('replaces the route and publishes no partial aggregate when one request fails', async () => {
    // Given
    const fixture = makeAggregate('project-1', 'one');
    let rejectExports: ((reason?: unknown) => void) | undefined;
    const exportRequest = new Promise<{ exports: StudioExport[] }>((_resolve, reject) => {
      rejectExports = reject;
    });
    vi.mocked(api.session).mockResolvedValue(fixture.session);
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
      rejectExports(new Error('exports unavailable'));
      await exportRequest.catch(() => undefined);
      await Promise.resolve();
    });

    // Then
    expect(harness.result().pathname).toBe('/');
    expect(harness.result().navigationType).toBe('REPLACE');
    expect(harness.result().hook.session).toBeNull();
    expect(harness.result().hook.project).toBeNull();
    expect(harness.result().hook.reviews).toEqual([]);
    expect(harness.result().hook.exports).toEqual([]);
  });

  it('publishes the new aggregate when the project id changes', async () => {
    // Given
    const first = makeAggregate('project-1', 'one');
    const second = makeAggregate('project-2', 'two');
    vi.mocked(api.session)
      .mockResolvedValueOnce(first.session)
      .mockResolvedValueOnce(second.session);
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
    expect(firstPublished.session).toEqual(first.session);
    expect(firstPublished.project).toEqual(first.project);
    expect(firstPublished.reviews).toEqual([first.review]);
    expect(firstPublished.exports).toEqual([first.studioExport]);
    expect(harness.result().hook.session).toEqual(second.session);
    expect(harness.result().hook.project).toEqual(second.project);
    expect(harness.result().hook.reviews).toEqual([second.review]);
    expect(harness.result().hook.exports).toEqual([second.studioExport]);
    expect(api.project).toHaveBeenNthCalledWith(1, 'project-1');
    expect(api.project).toHaveBeenNthCalledWith(2, 'project-2');
  });
});
