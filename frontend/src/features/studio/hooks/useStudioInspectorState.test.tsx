import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Project } from '@/app/types/studio';

import { useStudioInspectorState } from './useStudioInspectorState';

type HookArgs = Parameters<typeof useStudioInspectorState>[0];
type HookResult = ReturnType<typeof useStudioInspectorState>;

const mountedRoots: Array<{ container: HTMLDivElement; root: Root }> = [];

afterEach(() => {
  for (const { container, root } of mountedRoots) {
    act(() => {
      root.unmount();
    });
    container.remove();
  }
  mountedRoots.length = 0;
});

function renderInspectorHook(initialArgs: HookArgs): {
  readonly result: () => HookResult;
  readonly rerender: (nextArgs: HookArgs) => void;
} {
  let hookArgs = initialArgs;
  let current: HookResult | undefined;

  function Wrapper(): null {
    current = useStudioInspectorState(hookArgs);
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
    rerender: (nextArgs: HookArgs) => {
      hookArgs = nextArgs;
      act(() => {
        root.render(<Wrapper />);
      });
    },
  };
}

const baseProject: Project = {
  id: 'project-1',
  title: 'Clockwork Harbor',
  description: 'A harbor of brass clocks.',
  settings: { provider: 'dashscope' },
  import_hash: null,
  created_at: '2026-06-16T00:00:00Z',
  updated_at: '2026-06-16T00:00:00Z',
  documents: [],
};

describe('useStudioInspectorState', () => {
  it('selects the matching inspector tab when route sections change', () => {
    const loadJobs = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
    const hook = renderInspectorHook({
      section: 'manuscript',
      project: baseProject,
      loadJobs,
    });

    expect(hook.result().inspector).toBe('copilot');

    hook.rerender({ section: 'review', project: baseProject, loadJobs });
    expect(hook.result().inspector).toBe('review');

    hook.rerender({ section: 'history', project: baseProject, loadJobs });
    expect(hook.result().inspector).toBe('history');

    hook.rerender({ section: 'export', project: baseProject, loadJobs });
    expect(hook.result().inspector).toBe('export');

    hook.rerender({ section: 'settings', project: baseProject, loadJobs });
    expect(hook.result().inspector).toBe('settings');
    expect(loadJobs).not.toHaveBeenCalled();
  });

  it('loads jobs only when the jobs inspector is selected', () => {
    const loadJobs = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
    const hook = renderInspectorHook({
      section: 'manuscript',
      project: baseProject,
      loadJobs,
    });

    expect(loadJobs).not.toHaveBeenCalled();

    act(() => {
      hook.result().setInspector('jobs');
    });

    expect(hook.result().inspector).toBe('jobs');
    expect(loadJobs).toHaveBeenCalledTimes(1);
  });

  it('copies the selected project into settings form state', () => {
    const loadJobs = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
    const hook = renderInspectorHook({
      section: 'settings',
      project: baseProject,
      loadJobs,
    });

    expect(hook.result().settingsForm).toEqual({
      title: 'Clockwork Harbor',
      description: 'A harbor of brass clocks.',
      provider: 'dashscope',
    });

    hook.rerender({
      section: 'settings',
      project: {
        ...baseProject,
        title: 'Mock Harbor',
        description: '',
        settings: {},
      },
      loadJobs,
    });

    expect(hook.result().settingsForm).toEqual({
      title: 'Mock Harbor',
      description: '',
      provider: 'mock',
    });
  });
});
