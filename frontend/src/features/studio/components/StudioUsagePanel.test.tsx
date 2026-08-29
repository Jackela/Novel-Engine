import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/app/api';
import type { ProjectUsage } from '@/app/types/studio';

import { StudioUsagePanel } from './StudioUsagePanel';

vi.mock('@/app/api', () => ({
  api: { usage: vi.fn() },
}));

const mountedRoots: Array<{ container: HTMLDivElement; root: Root }> = [];

afterEach(() => {
  for (const { container, root } of mountedRoots) {
    act(() => root.unmount());
    container.remove();
  }
  mountedRoots.length = 0;
  vi.clearAllMocks();
});

function renderUsagePanel(active: boolean): HTMLDivElement {
  const container = document.createElement('div');
  const root = createRoot(container);
  mountedRoots.push({ container, root });
  act(() => {
    root.render(<StudioUsagePanel active={active} projectId="project-1" />);
  });
  return container;
}

const emptyUsage: ProjectUsage = {
  project_id: 'project-1',
  request_count: 0,
  prompt_tokens: 0,
  completion_tokens: 0,
  per_model: [],
};

const multiModelUsage: ProjectUsage = {
  project_id: 'project-1',
  request_count: 1234,
  prompt_tokens: 120000,
  completion_tokens: 4500,
  per_model: [
    {
      model: 'qwen-max',
      requests: 1000,
      prompt_tokens: 100000,
      completion_tokens: 4000,
    },
    {
      model: 'mock',
      requests: 234,
      prompt_tokens: 20000,
      completion_tokens: 500,
    },
  ],
};

function flush(): Promise<void> {
  return act(async () => {
    await Promise.resolve();
  });
}

describe('StudioUsagePanel', () => {
  beforeEach(() => {
    vi.mocked(api.usage).mockResolvedValue(emptyUsage);
  });

  it('renders an empty state without a per-model table when usage is empty', async () => {
    const container = renderUsagePanel(true);
    await flush();

    expect(api.usage).toHaveBeenCalledWith('project-1');
    expect(container.querySelector('.usage-table')).toBeNull();
    expect(container.textContent).toContain('No usage recorded yet.');
    expect(container.textContent).toContain('0');
  });

  it('renders totals cards and a per-model row per model with thousands separators', async () => {
    vi.mocked(api.usage).mockResolvedValue(multiModelUsage);
    const container = renderUsagePanel(true);
    await flush();

    const cards = Array.from(container.querySelectorAll('.usage-total-card'));
    expect(cards.map((card) => card.textContent)).toEqual([
      '1,234Requests',
      '120,000Prompt tokens',
      '4,500Completion tokens',
    ]);

    const rows = Array.from(container.querySelectorAll('.usage-table tbody tr'));
    expect(rows).toHaveLength(2);
    expect(rows[0].textContent).toContain('qwen-max');
    expect(rows[0].textContent).toContain('100,000');
    expect(rows[1].textContent).toContain('mock');
    expect(rows[1].textContent).toContain('500');
  });

  it('does not fetch while the tab is inactive', async () => {
    renderUsagePanel(false);
    await flush();
    expect(api.usage).not.toHaveBeenCalled();
  });
});
