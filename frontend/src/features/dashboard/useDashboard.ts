import { useEffect, useRef, useState } from 'react';

import { api } from '@/app/api';
import type {
  DashboardStatus,
  OrchestrationStatus,
} from '@/app/types';
import { characterRoster, worldBeats } from '@/features/dashboard/dashboardContent';

interface UseDashboardResult {
  status: DashboardStatus | null;
  orchestration: OrchestrationStatus | null;
  characters: typeof characterRoster;
  world: typeof worldBeats;
  isRefreshing: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  start: () => Promise<void>;
  pause: () => Promise<void>;
  stop: () => Promise<void>;
}

const emptyStatus: DashboardStatus = {
  status: 'offline',
  mode: 'remote',
  workspaceId: '',
  headline: 'Waiting for workspace context',
  summary: 'No dashboard data loaded yet.',
  activeCharacters: 0,
  activeSignals: 0,
};

export function useDashboard(workspaceId: string): UseDashboardResult {
  const [status, setStatus] = useState<DashboardStatus | null>(null);
  const [orchestration, setOrchestration] = useState<OrchestrationStatus | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const workspaceIdRef = useRef(workspaceId);
  const requestVersionRef = useRef(0);

  useEffect(() => {
    workspaceIdRef.current = workspaceId;
  }, [workspaceId]);

  const loadDashboard = async (targetWorkspaceId: string, requestVersion: number) => {
    setIsRefreshing(true);
    setError(null);
    try {
      const [nextStatus, nextOrchestration] = await Promise.all([
        api.getDashboardStatus(targetWorkspaceId),
        api.getOrchestrationStatus(targetWorkspaceId),
      ]);

      if (
        workspaceIdRef.current !== targetWorkspaceId ||
        requestVersion !== requestVersionRef.current
      ) {
        return;
      }

      setStatus(nextStatus);
      setOrchestration(nextOrchestration);
    } catch (nextError) {
      if (
        workspaceIdRef.current !== targetWorkspaceId ||
        requestVersion !== requestVersionRef.current
      ) {
        return;
      }

      setError(nextError instanceof Error ? nextError.message : 'Unable to load dashboard.');
    } finally {
      if (
        workspaceIdRef.current === targetWorkspaceId &&
        requestVersion === requestVersionRef.current
      ) {
        setIsRefreshing(false);
      }
    }
  };

  const refresh = async (targetWorkspaceId: string = workspaceIdRef.current) => {
    if (workspaceIdRef.current !== targetWorkspaceId) {
      return;
    }

    const requestVersion = ++requestVersionRef.current;
    await loadDashboard(targetWorkspaceId, requestVersion);
  };

  useEffect(() => {
    setStatus(null);
    setOrchestration(null);
    setError(null);
    const requestVersion = ++requestVersionRef.current;

    void loadDashboard(workspaceId, requestVersion);

    return () => {
      requestVersionRef.current += 1;
    };
  }, [workspaceId]);

  useEffect(() => {
    if (orchestration?.status !== 'running') {
      return;
    }

    const intervalId = window.setInterval(() => {
      void refresh();
    }, 2500);

    return () => window.clearInterval(intervalId);
  }, [orchestration?.status, workspaceId]);

  return {
    status: status ?? { ...emptyStatus, workspaceId },
    orchestration,
    characters: characterRoster,
    world: worldBeats,
    isRefreshing,
    error,
    refresh,
    async start() {
      const targetWorkspaceId = workspaceIdRef.current;

      await api.startOrchestration(targetWorkspaceId);
      await refresh(targetWorkspaceId);
    },
    async pause() {
      const targetWorkspaceId = workspaceIdRef.current;

      await api.pauseOrchestration(targetWorkspaceId);
      await refresh(targetWorkspaceId);
    },
    async stop() {
      const targetWorkspaceId = workspaceIdRef.current;

      await api.stopOrchestration(targetWorkspaceId);
      await refresh(targetWorkspaceId);
    },
  };
}
