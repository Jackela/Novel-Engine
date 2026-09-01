import { useCallback, useEffect, useRef, useState } from "react";

import { api, HttpError } from "@/app/api";
import type { Project } from "@/app/types/studio";

import { toErrorMessage } from "./toErrorMessage";

interface ProjectLibraryBootstrapState {
  readonly projects: Project[];
  readonly error: string | null;
  readonly isLoading: boolean;
  readonly hasLoaded: boolean;
}

const INITIAL_STATE: ProjectLibraryBootstrapState = {
  projects: [],
  error: null,
  isLoading: true,
  hasLoaded: false,
};

/** Verifies the session before loading projects and owns both cancellable reads. */
export function useProjectLibraryBootstrap(onUnauthenticated: () => void) {
  const [state, setState] = useState<ProjectLibraryBootstrapState>(INITIAL_STATE);
  const mountedRef = useRef(false);
  const requestRef = useRef(0);
  const controllerRef = useRef<AbortController | null>(null);
  const inFlightReloadRef = useRef<Promise<void> | null>(null);

  const reload = useCallback((): Promise<void> => {
    if (inFlightReloadRef.current !== null) return inFlightReloadRef.current;
    const run = (async () => {
      const request = requestRef.current + 1;
      requestRef.current = request;
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      const isCurrent = () =>
        mountedRef.current && requestRef.current === request && !controller.signal.aborted;

      setState((current) => ({ ...current, isLoading: true }));
      try {
        await api.session({ signal: controller.signal });
        if (!isCurrent()) return;
        const response = await api.projects({ signal: controller.signal });
        if (isCurrent()) {
          setState({ projects: response.projects, error: null, isLoading: false, hasLoaded: true });
        }
      } catch (reason) {
        if (!isCurrent()) return;
        if (reason instanceof HttpError && reason.status === 401) {
          onUnauthenticated();
          return;
        }
        setState((current) => ({
          ...current,
          error: toErrorMessage(reason, "Unable to load projects."),
          isLoading: false,
        }));
      }
    })();

    let tracked: Promise<void>;
    tracked = run.finally(() => {
      if (inFlightReloadRef.current === tracked) inFlightReloadRef.current = null;
    });
    inFlightReloadRef.current = tracked;
    return tracked;
  }, [onUnauthenticated]);

  useEffect(() => {
    mountedRef.current = true;
    void reload();
    return () => {
      mountedRef.current = false;
      requestRef.current += 1;
      inFlightReloadRef.current = null;
      controllerRef.current?.abort();
      controllerRef.current = null;
    };
  }, [reload]);

  return { ...state, reload, mountedRef };
}
