import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { NavigateFunction } from "react-router-dom";

import { api, HttpError } from "@/app/api";
import type { Project } from "@/app/types/studio";

import type { ProjectShellReadCapture } from "./projectShellReadAuthority";
import { resolveStateAction } from "./resolveStateAction";

interface ProjectState {
  readonly projectId: string;
  readonly project: Project | null;
}

interface ScopedErrorState {
  readonly projectId: string;
  readonly value: string | null;
}

/**
 * The route project identity owns the bounded project shell and its action
 * error channel. Scoped projections hide prior-project state synchronously
 * before the next effect, while read authority (capture/publish epochs)
 * rejects shell reads that race local mutations or a newer owner. The shell
 * load lifecycle (`useProjectShellLoad`) collaborates through the narrow
 * surface below: the active-identity gate, the dedicated writes for its
 * winning read, and the action error channel.
 */
export function useProjectShellState(projectId: string, navigate: NavigateFunction) {
  // react-router re-creates `navigate` on every pathname change; the absence
  // and authentication redirects read the latest `navigate` through a ref and
  // stay identity-stable (#465). The ref updates in an effect, never during
  // render.
  const navigateRef = useRef(navigate);
  useEffect(() => {
    navigateRef.current = navigate;
  }, [navigate]);
  const activeProjectIdRef = useRef<string | null>(null);
  const projectMutationEpochRef = useRef(0);
  const nextProjectReadEpochRef = useRef(0);
  const publishedProjectReadEpochRef = useRef(0);
  const [projectState, setProjectState] = useState<ProjectState>(() => ({
    projectId,
    project: null,
  }));
  const [errorState, setErrorState] = useState<ScopedErrorState>(() => ({
    projectId,
    value: null,
  }));

  useEffect(() => {
    activeProjectIdRef.current = projectId;
    return () => {
      if (activeProjectIdRef.current === projectId) {
        activeProjectIdRef.current = null;
      }
      projectMutationEpochRef.current += 1;
      publishedProjectReadEpochRef.current = ++nextProjectReadEpochRef.current;
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
      readEpoch: ++nextProjectReadEpochRef.current,
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
        capture.readEpoch < publishedProjectReadEpochRef.current ||
        capture.mutationEpoch !== projectMutationEpochRef.current
      )
        return false;
      publishedProjectReadEpochRef.current = capture.readEpoch;
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
          navigateRef.current("/", { replace: true });
          return false;
        }
        if (reason instanceof HttpError && reason.status === 404) {
          navigateRef.current("/projects", { replace: true });
          return false;
        }
        throw reason;
      }
    },
    [captureProjectShellRead, projectId, publishProjectShellRead],
  );

  const isActiveProject = useCallback(() => activeProjectIdRef.current === projectId, [projectId]);

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

  const beginShellLoad = useCallback(() => {
    publishedProjectReadEpochRef.current = ++nextProjectReadEpochRef.current;
    setProjectState({ projectId, project: null });
  }, [projectId]);

  const commitLoadedShell = useCallback(
    (nextProject: Project) => {
      setProjectState({ projectId, project: nextProject });
    },
    [projectId],
  );

  const stateIsCurrent = projectState.projectId === projectId;
  const project = stateIsCurrent ? projectState.project : null;
  const error = errorState.projectId === projectId ? errorState.value : null;

  return {
    project,
    setProject,
    error,
    setError,
    captureProjectShellRead,
    publishProjectShellRead,
    recheckProject,
    isActiveProject,
    beginShellLoad,
    commitLoadedShell,
  };
}
