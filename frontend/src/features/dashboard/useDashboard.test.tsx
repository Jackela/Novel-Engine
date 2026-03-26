import { act } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/app/api';

import { render, screen, waitFor } from '../../../tests/test-utils';
import { useDashboard } from './useDashboard';

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
};

function createDeferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });

  return { promise, resolve };
}

function DashboardProbe({ workspaceId }: { workspaceId: string }) {
  const { status, orchestration, isRefreshing } = useDashboard(workspaceId);

  return (
    <div>
      <span data-testid="workspace-id">{status?.workspaceId ?? 'empty'}</span>
      <span data-testid="headline">{status?.headline ?? 'empty'}</span>
      <span data-testid="turn">{orchestration?.current_turn ?? 'none'}</span>
      <span data-testid="refreshing">{isRefreshing ? 'yes' : 'no'}</span>
    </div>
  );
}

describe('useDashboard', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('ignores stale workspace refreshes when the workspace changes', async () => {
    const firstStatus = createDeferred<Awaited<ReturnType<typeof api.getDashboardStatus>>>();
    const firstOrchestration = createDeferred<
      Awaited<ReturnType<typeof api.getOrchestrationStatus>>
    >();
    const secondStatus = createDeferred<Awaited<ReturnType<typeof api.getDashboardStatus>>>();
    const secondOrchestration = createDeferred<
      Awaited<ReturnType<typeof api.getOrchestrationStatus>>
    >();

    vi.spyOn(api, 'getDashboardStatus').mockImplementation((workspaceId) => {
      if (workspaceId === 'workspace-one') {
        return firstStatus.promise;
      }

      if (workspaceId === 'workspace-two') {
        return secondStatus.promise;
      }

      throw new Error(`Unexpected workspace: ${workspaceId}`);
    });
    vi.spyOn(api, 'getOrchestrationStatus').mockImplementation((workspaceId) => {
      if (workspaceId === 'workspace-one') {
        return firstOrchestration.promise;
      }

      if (workspaceId === 'workspace-two') {
        return secondOrchestration.promise;
      }

      throw new Error(`Unexpected workspace: ${workspaceId}`);
    });

    const { rerender } = render(<DashboardProbe workspaceId="workspace-one" />);

    rerender(<DashboardProbe workspaceId="workspace-two" />);

    await act(async () => {
      secondStatus.resolve({
        status: 'healthy',
        mode: 'remote',
        workspaceId: 'workspace-two',
        headline: 'Second workspace',
        summary: 'Current workspace snapshot.',
        activeCharacters: 2,
        activeSignals: 1,
      });
      secondOrchestration.resolve({
        status: 'running',
        current_turn: 2,
        total_turns: 3,
        queue_length: 0,
        average_processing_time: 1.2,
        steps: [],
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId('workspace-id')).toHaveTextContent('workspace-two');
      expect(screen.getByTestId('headline')).toHaveTextContent('Second workspace');
      expect(screen.getByTestId('turn')).toHaveTextContent('2');
    });

    await act(async () => {
      firstStatus.resolve({
        status: 'healthy',
        mode: 'remote',
        workspaceId: 'workspace-one',
        headline: 'Stale workspace',
        summary: 'This response should be ignored.',
        activeCharacters: 1,
        activeSignals: 0,
      });
      firstOrchestration.resolve({
        status: 'idle',
        current_turn: 0,
        total_turns: 0,
        queue_length: 0,
        average_processing_time: 0,
        steps: [],
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId('workspace-id')).toHaveTextContent('workspace-two');
      expect(screen.getByTestId('headline')).toHaveTextContent('Second workspace');
      expect(screen.getByTestId('turn')).toHaveTextContent('2');
    });
  });
});
