import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { NavigateFunction } from "react-router-dom";

import { api, HttpError } from "@/app/api";
import { translateActive } from "@/app/i18n/translate";
import type { Project } from "@/app/types/studio";
import { toErrorMessage } from "./toErrorMessage";

const DEFAULT_LOAD_ERROR = (): string => translateActive("errors.loadProject");

interface ScopedErrorState {
  readonly projectId: string;
  readonly value: string | null;
}

interface ScopedLoadingState {
  readonly projectId: string;
  readonly value: boolean;
}

interface ProjectLoadRequest {
  readonly projectId: string;
  readonly controller: AbortController;
  readonly epoch: number;
  promise: Promise<void>;
}

/**
 * Collaborators owned by the project shell state: the active-identity gate
 * for completion checks, the shell writes reserved for the winning
 * bootstrap/retry read, the shared navigation identity, and the action error
 * channel.
 */
interface ProjectShellLoadCollaborators {
  readonly navigate: NavigateFunction;
  readonly isActiveProject: () => boolean;
  readonly setError: Dispatch<SetStateAction<string | null>>;
  readonly beginShellLoad: () => void;
  readonly commitLoadedShell: (nextProject: Project) => void;
}

/**
 * The bootstrap/retry load lifecycle for the project shell. Cancellation plus
 * a request epoch prevents stale completion; retries coalesce while a load is
 * in flight. Authentication and absence navigate deliberately; operational
 * failures stay on the requested route and expose `retryLoad`.
 */
export function useProjectShellLoad(
  projectId: string,
  collaborators: ProjectShellLoadCollaborators,
) {
  const { navigate, isActiveProject, setError, beginShellLoad, commitLoadedShell } = collaborators;
  // react-router re-creates `navigate` on every pathname change; the absence
  // and authentication redirects read the latest `navigate` through a ref so
  // `retryLoad` stays identity-stable per project (#465). The ref updates in
  // an effect, never during render.
  const navigateRef = useRef(navigate);
  useEffect(() => {
    navigateRef.current = navigate;
  }, [navigate]);
  const requestEpochRef = useRef(0);
  const requestRef = useRef<ProjectLoadRequest | null>(null);
  const [loadErrorState, setLoadErrorState] = useState<ScopedErrorState>(() => ({
    projectId,
    value: null,
  }));
  const [loadingState, setLoadingState] = useState<ScopedLoadingState>(() => ({
    projectId,
    value: false,
  }));

  useEffect(() => {
    return () => {
      const request = requestRef.current;
      if (request?.projectId === projectId) {
        request.controller.abort();
        requestRef.current = null;
      }
      requestEpochRef.current += 1;
    };
  }, [projectId]);

  const retryLoad = useCallback((): Promise<void> => {
    if (!isActiveProject()) return Promise.resolve();
    const inFlight = requestRef.current;
    if (
      inFlight?.projectId === projectId &&
      !inFlight.controller.signal.aborted &&
      inFlight.epoch === requestEpochRef.current
    ) {
      return inFlight.promise;
    }

    const controller = new AbortController();
    beginShellLoad();
    const requestEpoch = ++requestEpochRef.current;
    const request: ProjectLoadRequest = {
      projectId,
      controller,
      epoch: requestEpoch,
      promise: Promise.resolve(),
    };
    requestRef.current = request;
    setLoadingState({ projectId, value: true });

    const isCurrentRequest = () =>
      !controller.signal.aborted &&
      requestRef.current === request &&
      requestEpochRef.current === requestEpoch &&
      isActiveProject();

    request.promise = (async () => {
      let shellPublished = false;
      try {
        const nextProject = await api.project(projectId, { signal: controller.signal });
        if (!isCurrentRequest()) return;
        shellPublished = true;
        commitLoadedShell(nextProject);
        setLoadErrorState({ projectId, value: null });
        setLoadingState({ projectId, value: false });
      } catch (reason) {
        if (!isCurrentRequest()) return;
        controller.abort();
        if (reason instanceof HttpError && reason.status === 401) {
          navigateRef.current("/", { replace: true });
          return;
        }
        if (!shellPublished && reason instanceof HttpError && reason.status === 404) {
          navigateRef.current("/projects", { replace: true });
          return;
        }
        const message = toErrorMessage(reason, DEFAULT_LOAD_ERROR());
        if (shellPublished) setError(message);
        else setLoadErrorState({ projectId, value: message });
      } finally {
        if (requestRef.current === request) {
          requestRef.current = null;
          if (isActiveProject()) {
            setLoadingState({ projectId, value: false });
          }
        }
      }
    })();

    return request.promise;
  }, [beginShellLoad, commitLoadedShell, isActiveProject, projectId, setError]);

  // Bootstrap is keyed by the route project identity only; `retryLoad` is
  // stable for one projectId, so same-project pathname changes (section and
  // route-inspector navigation) never replay the shell read (#465).
  useEffect(() => {
    void retryLoad();
  }, [retryLoad]);

  const loadError = loadErrorState.projectId === projectId ? loadErrorState.value : null;
  const isLoading = loadingState.projectId === projectId ? loadingState.value : false;

  return { loadError, isLoading, retryLoad };
}
