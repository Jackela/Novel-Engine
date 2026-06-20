import { act, useState } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/app/api';
import type { StudioJob } from '@/app/types/studio';

import { useStudioJobs } from './useStudioJobs';
import { useStudioSearch } from './useStudioSearch';

vi.mock('@/app/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/app/api')>();
  return {
    ...actual,
    api: {
      ...actual.api,
      jobs: vi.fn<typeof actual.api.jobs>(),
      search: vi.fn<typeof actual.api.search>(),
    },
  };
});

interface HarnessSnapshot {
  readonly jobs: ReturnType<typeof useStudioJobs>;
  readonly search: ReturnType<typeof useStudioSearch>;
  readonly error: string | null;
}

const job: StudioJob = {
  id: 'job-1',
  project_id: 'project-1',
  document_id: 'document-1',
  kind: 'proposal',
  operation: 'continue',
  status: 'completed',
  provider: 'mock',
  model: 'studio-copilot-v1',
  request: {},
  result: {},
  error: null,
  retry_of_job_id: null,
  events: [],
  created_at: '2026-06-20T00:00:00Z',
  updated_at: '2026-06-20T00:00:00Z',
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

function renderQueryHooks(): {
  readonly result: () => HarnessSnapshot;
  readonly submitSearch: () => void;
} {
  let current: HarnessSnapshot | undefined;

  function Wrapper() {
    const [error, setError] = useState<string | null>(null);
    const jobs = useStudioJobs('project-1', setError);
    const search = useStudioSearch('project-1', setError);
    current = { jobs, search, error };
    return <form onSubmit={search.runSearch} />;
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
    throw new Error('Expected search form after render.');
  }

  return {
    result: () => {
      if (current === undefined) {
        throw new Error('Expected query hook result after render.');
      }
      return current;
    },
    submitSearch: () => {
      form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    },
  };
}

describe('Studio query hooks', () => {
  it('publishes search results and returns to the idle state', async () => {
    // Given
    const results = [{ document_id: 'document-1', title: 'Chapter', excerpt: 'Clockwork' }];
    vi.mocked(api.search).mockResolvedValue({ results });
    const harness = renderQueryHooks();
    act(() => {
      harness.result().search.setSearch('clockwork');
    });

    // When
    await act(async () => {
      harness.submitSearch();
    });

    // Then
    expect(harness.result().search.searchResults).toEqual(results);
    expect(harness.result().search.isSearching).toBe(false);
    expect(harness.result().error).toBeNull();
  });

  it('skips whitespace-only searches and clears prior results', async () => {
    // Given
    vi.mocked(api.search).mockResolvedValue({
      results: [{ document_id: 'document-1', title: 'Chapter', excerpt: 'Clockwork' }],
    });
    const harness = renderQueryHooks();
    act(() => {
      harness.result().search.setSearch('clockwork');
    });
    await act(async () => {
      harness.submitSearch();
    });

    // When
    act(() => {
      harness.result().search.setSearch('   ');
    });
    await act(async () => {
      harness.submitSearch();
    });

    // Then
    expect(harness.result().search.searchResults).toEqual([]);
    expect(api.search).toHaveBeenCalledTimes(1);
  });

  it('reports a search failure and resets the searching state', async () => {
    // Given
    vi.mocked(api.search).mockRejectedValue(new Error('search unavailable'));
    const harness = renderQueryHooks();
    act(() => {
      harness.result().search.setSearch('clockwork');
    });

    // When
    await act(async () => {
      harness.submitSearch();
    });

    // Then
    expect(harness.result().error).toBe('search unavailable');
    expect(harness.result().search.isSearching).toBe(false);
  });

  it('loads jobs into observable hook state', async () => {
    // Given
    vi.mocked(api.jobs).mockResolvedValue({ jobs: [job] });
    const harness = renderQueryHooks();

    // When
    await act(async () => {
      await harness.result().jobs.loadJobs();
    });

    // Then
    expect(harness.result().jobs.jobs).toEqual([job]);
    expect(harness.result().error).toBeNull();
  });

  it('reports a jobs loading failure', async () => {
    // Given
    vi.mocked(api.jobs).mockRejectedValue(new Error('jobs unavailable'));
    const harness = renderQueryHooks();

    // When
    await act(async () => {
      await harness.result().jobs.loadJobs();
    });

    // Then
    expect(harness.result().jobs.jobs).toEqual([]);
    expect(harness.result().error).toBe('jobs unavailable');
  });
});
