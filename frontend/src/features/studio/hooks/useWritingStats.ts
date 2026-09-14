import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/app/api";
import { translateActive } from "@/app/i18n/translate";
import type { WritingStats } from "@/app/types/studio";
import { toErrorMessage } from "./toErrorMessage";

interface WritingStatsState {
  readonly projectId: string;
  readonly stats: WritingStats | null;
  readonly isLoading: boolean;
  readonly error: string | null;
}

/**
 * Loads the project writing-statistics summary (#653) lazily: the request
 * fires the first time the Stats inspector tab becomes active, and can be
 * repeated through the panel's refresh command. A refresh aborts the in-flight
 * request, so a duplicate submission never double-publishes.
 */
export function useWritingStats(projectId: string, active: boolean) {
  const activeProjectIdRef = useRef<string | null>(null);
  const controllerRef = useRef<{
    readonly projectId: string;
    readonly controller: AbortController;
  } | null>(null);
  const requestEpochRef = useRef(0);
  const autoLoadedProjectIdRef = useRef<string | null>(null);
  const [state, setState] = useState<WritingStatsState>(() => ({
    projectId,
    stats: null,
    isLoading: false,
    error: null,
  }));

  useEffect(() => {
    activeProjectIdRef.current = projectId;
    return () => {
      if (activeProjectIdRef.current === projectId) {
        activeProjectIdRef.current = null;
      }
      if (controllerRef.current?.projectId === projectId) {
        controllerRef.current.controller.abort();
        controllerRef.current = null;
      }
      if (autoLoadedProjectIdRef.current === projectId) {
        autoLoadedProjectIdRef.current = null;
      }
      requestEpochRef.current += 1;
    };
  }, [projectId]);

  const loadStats = useCallback(async () => {
    if (activeProjectIdRef.current !== projectId) return;
    controllerRef.current?.controller.abort();
    const controller = new AbortController();
    controllerRef.current = { projectId, controller };
    const requestEpoch = ++requestEpochRef.current;
    setState((current) => ({
      projectId,
      stats: current.projectId === projectId ? current.stats : null,
      isLoading: true,
      error: current.projectId === projectId ? current.error : null,
    }));

    const isCurrentRequest = () =>
      !controller.signal.aborted &&
      requestEpochRef.current === requestEpoch &&
      activeProjectIdRef.current === projectId;

    try {
      const response = await api.writingStats(projectId, { signal: controller.signal });
      if (!isCurrentRequest()) return;
      setState({ projectId, stats: response, isLoading: false, error: null });
    } catch (reason) {
      if (!isCurrentRequest()) return;
      setState((current) => ({
        projectId,
        stats: current.projectId === projectId ? current.stats : null,
        isLoading: false,
        error: toErrorMessage(reason, translateActive("errors.loadStats")),
      }));
    }
  }, [projectId]);

  useEffect(() => {
    if (active && autoLoadedProjectIdRef.current !== projectId) {
      autoLoadedProjectIdRef.current = projectId;
      void loadStats();
    }
  }, [active, loadStats, projectId]);

  const stateIsCurrent = state.projectId === projectId;
  const stats = stateIsCurrent ? state.stats : null;
  const isLoading = stateIsCurrent ? state.isLoading : false;
  const error = stateIsCurrent ? state.error : null;

  return { stats, isLoading, error, reload: loadStats };
}
