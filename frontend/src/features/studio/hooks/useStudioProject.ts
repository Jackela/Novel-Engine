import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, HttpError } from "@/app/api";
import type { Project } from "@/app/types/studio";

import type { ProjectShellReadCapture } from "./projectShellReadAuthority";
import { toErrorMessage } from "./toErrorMessage";

const DEFAULT_LOAD_ERROR = "Unable to load the project. Please retry.";

interface ProjectState {
  readonly projectId: string;
  readonly project: Project | null;
}

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

function resolveStateAction<T>(current: T, action: SetStateAction<T>): T {
  return typeof action === "function" ? (action as (value: T) => T)(current) : action;
}

/**
 * The route project identity owns the bounded project shell and its errors.
 * Cancellation plus a request epoch prevents stale completion, while scoped
 * projections hide prior-project state synchronously before the next effect.
 * Authentication and absence navigate deliberately; operational failures stay
 * on the requested route and expose `retryLoad`.
 */
export function useStudioProject(projectId: string) {
  const navigate = useNavigate();
  const [lifecycle] = useState(() => Symbol("studio lifecycle"));
  const activeProjectIdRef = useRef<string | null>(null);
  const projectMutationEpochRef = useRef(0);
  const projectReadEpochRef = useRef(0);
  const requestEpochRef = useRef(0);
  const requestRef = useRef<ProjectLoadRequest | null>(null);
  const [projectState, setProjectState] = useState<ProjectState>(() => ({
    projectId,
    project: null,
  }));
  const [errorState, setErrorState] = useState<ScopedErrorState>(() => ({
    projectId,
    value: null,
  }));
  const [loadErrorState, setLoadErrorState] = useState<ScopedErrorState>(() => ({
    projectId,
    value: null,
  }));
  const [loadingState, setLoadingState] = useState<ScopedLoadingState>(() => ({
    projectId,
    value: false,
  }));

  useEffect(() => {
    activeProjectIdRef.current = projectId;
    return () => {
      if (activeProjectIdRef.current === projectId) {
        activeProjectIdRef.current = null;
      }
      const request = requestRef.current;
      if (request?.projectId === projectId) {
        request.controller.abort();
        requestRef.current = null;
      }
      requestEpochRef.current += 1;
      projectMutationEpochRef.current += 1;
      projectReadEpochRef.current += 1;
    };
  }, [projectId]);

  const setProject = useCallback<Dispatch<SetStateAction<Project | null>>>(
    (nextProject) => {
      if (activeProjectIdRef.current !== projectId) return;
      projectMutationEpochRef.current += 1;
      setProjectState((current) => {
        if (activeProjectIdRef.current !== projectId) return current;
        const currentProject = current.projectId === projectId ? current.project : null;
        return {
          projectId,
          project: resolveStateAction(currentProject, nextProject),
        };
      });
    },
    [projectId],
  );

  const captureProjectShellRead = useCallback(
    (): ProjectShellReadCapture => ({
      projectId,
      readEpoch: ++projectReadEpochRef.current,
      mutationEpoch: projectMutationEpochRef.current,
    }),
    [projectId],
  );

  const publishProjectShellRead = useCallback(
    (capture: ProjectShellReadCapture, nextProject: Project): boolean => {
      if (
        activeProjectIdRef.current !== projectId ||
        capture.projectId !== projectId ||
        nextProject.id !== projectId ||
        nextProject.documents.some((document) => document.project_id !== projectId) ||
        nextProject.volumes.some((volume) => volume.project_id !== projectId) ||
        capture.readEpoch !== projectReadEpochRef.current ||
        capture.mutationEpoch !== projectMutationEpochRef.current
      )
        return false;
      setProjectState(() => ({
        projectId,
        project: nextProject,
      }));
      return true;
    },
    [projectId],
  );

  const recheckProject = useCallback(
    async (signal: AbortSignal): Promise<boolean> => {
      const capture = captureProjectShellRead();
      try {
        const nextProject = await api.project(projectId, { signal });
        if (signal.aborted || activeProjectIdRef.current !== projectId) return false;
        publishProjectShellRead(capture, nextProject);
        return true;
      } catch (reason) {
        if (signal.aborted || activeProjectIdRef.current !== projectId) return false;
        if (reason instanceof HttpError && reason.status === 401) {
          navigate("/", { replace: true });
          return false;
        }
        if (reason instanceof HttpError && reason.status === 404) {
          navigate("/projects", { replace: true });
          return false;
        }
        throw reason;
      }
    },
    [captureProjectShellRead, navigate, projectId, publishProjectShellRead],
  );

  const setError = useCallback<Dispatch<SetStateAction<string | null>>>(
    (nextError) => {
      if (activeProjectIdRef.current !== projectId) return;
      setErrorState((current) => {
        if (activeProjectIdRef.current !== projectId) return current;
        const currentError = current.projectId === projectId ? current.value : null;
        return { projectId, value: resolveStateAction(currentError, nextError) };
      });
    },
    [projectId],
  );

  const retryLoad = useCallback((): Promise<void> => {
    if (activeProjectIdRef.current !== projectId) return Promise.resolve();
    const inFlight = requestRef.current;
    if (
      inFlight?.projectId === projectId &&
      !inFlight.controller.signal.aborted &&
      inFlight.epoch === requestEpochRef.current
    ) {
      return inFlight.promise;
    }

    const controller = new AbortController();
    projectReadEpochRef.current += 1;
    const requestEpoch = ++requestEpochRef.current;
    const request: ProjectLoadRequest = {
      projectId,
      controller,
      epoch: requestEpoch,
      promise: Promise.resolve(),
    };
    requestRef.current = request;
    setProjectState({ projectId, project: null });
    setLoadingState({ projectId, value: true });

    const isCurrentRequest = () =>
      !controller.signal.aborted &&
      requestRef.current === request &&
      requestEpochRef.current === requestEpoch &&
      activeProjectIdRef.current === projectId;

    request.promise = (async () => {
      let shellPublished = false;
      try {
        const nextProject = await api.project(projectId, { signal: controller.signal });
        if (!isCurrentRequest()) return;
        shellPublished = true;
        setProjectState({ projectId, project: nextProject });
        setLoadErrorState({ projectId, value: null });
        setLoadingState({ projectId, value: false });
      } catch (reason) {
        if (!isCurrentRequest()) return;
        controller.abort();
        if (reason instanceof HttpError && reason.status === 401) {
          navigate("/", { replace: true });
          return;
        }
        if (!shellPublished && reason instanceof HttpError && reason.status === 404) {
          navigate("/projects", { replace: true });
          return;
        }
        const message = toErrorMessage(reason, DEFAULT_LOAD_ERROR);
        if (shellPublished) setErrorState({ projectId, value: message });
        else setLoadErrorState({ projectId, value: message });
      } finally {
        if (requestRef.current === request) {
          requestRef.current = null;
          if (activeProjectIdRef.current === projectId) {
            setLoadingState({ projectId, value: false });
          }
        }
      }
    })();

    return request.promise;
  }, [navigate, projectId]);

  useEffect(() => {
    void retryLoad();
  }, [retryLoad]);

  const stateIsCurrent = projectState.projectId === projectId;
  const project = stateIsCurrent ? projectState.project : null;
  const error = errorState.projectId === projectId ? errorState.value : null;
  const loadError = loadErrorState.projectId === projectId ? loadErrorState.value : null;
  const isLoading = loadingState.projectId === projectId ? loadingState.value : false;

  return {
    project,
    setProject,
    captureProjectShellRead,
    publishProjectShellRead,
    recheckProject,
    error,
    setError,
    loadError,
    isLoading,
    retryLoad,
    lifecycle,
  };
}
