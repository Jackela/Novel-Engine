import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/app/api";
import type { ProjectUsage } from "@/app/types/studio";

import { toErrorMessage } from "./toErrorMessage";

interface UsageState {
  readonly projectId: string;
  readonly usage: ProjectUsage | null;
  readonly isLoading: boolean;
  readonly error: string | null;
}

/**
 * Loads the project-level cumulative usage (#377) lazily: the request fires
 * the first time the Usage inspector tab becomes active, and can be repeated
 * through the panel's refresh command.
 */
export function useProjectUsage(projectId: string, active: boolean) {
  const activeProjectIdRef = useRef<string | null>(null);
  const controllerRef = useRef<{
    readonly projectId: string;
    readonly controller: AbortController;
  } | null>(null);
  const requestEpochRef = useRef(0);
  const autoLoadedProjectIdRef = useRef<string | null>(null);
  const [state, setState] = useState<UsageState>(() => ({
    projectId,
    usage: null,
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

  const loadUsage = useCallback(async () => {
    if (activeProjectIdRef.current !== projectId) return;
    controllerRef.current?.controller.abort();
    const controller = new AbortController();
    controllerRef.current = { projectId, controller };
    const requestEpoch = ++requestEpochRef.current;
    setState((current) => ({
      projectId,
      usage: current.projectId === projectId ? current.usage : null,
      isLoading: true,
      error: current.projectId === projectId ? current.error : null,
    }));

    const isCurrentRequest = () =>
      !controller.signal.aborted &&
      requestEpochRef.current === requestEpoch &&
      activeProjectIdRef.current === projectId;

    try {
      const response = await api.usage(projectId, { signal: controller.signal });
      if (!isCurrentRequest()) return;
      setState({ projectId, usage: response, isLoading: false, error: null });
    } catch (reason) {
      if (!isCurrentRequest()) return;
      setState((current) => ({
        projectId,
        usage: current.projectId === projectId ? current.usage : null,
        isLoading: false,
        error: toErrorMessage(reason, "Unable to load usage."),
      }));
    }
  }, [projectId]);

  useEffect(() => {
    if (active && autoLoadedProjectIdRef.current !== projectId) {
      autoLoadedProjectIdRef.current = projectId;
      void loadUsage();
    }
  }, [active, loadUsage, projectId]);

  const stateIsCurrent = state.projectId === projectId;
  const usage = stateIsCurrent ? state.usage : null;
  const isLoading = stateIsCurrent ? state.isLoading : false;
  const error = stateIsCurrent ? state.error : null;

  return { usage, isLoading, error, reload: loadUsage };
}
