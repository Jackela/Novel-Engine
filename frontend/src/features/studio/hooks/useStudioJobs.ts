import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/app/api";
import type { StudioJob } from "@/app/types/studio";

import { toErrorMessage } from "./toErrorMessage";

interface JobsState {
  readonly projectId: string;
  readonly jobs: StudioJob[];
  readonly isLoading: boolean;
  readonly loadingInitiator: JobsLoadInitiator | null;
}

export type JobsLoadInitiator = "auto" | "refresh" | "retry";

interface ActiveJobsRequest {
  readonly projectId: string;
  readonly controller: AbortController;
  promise: Promise<void>;
}

export function useStudioJobs(
  projectId: string,
  setError: Dispatch<SetStateAction<string | null>>,
) {
  const activeProjectIdRef = useRef<string | null>(null);
  const controllerRef = useRef<ActiveJobsRequest | null>(null);
  const requestEpochRef = useRef(0);
  const [state, setState] = useState<JobsState>(() => ({
    projectId,
    jobs: [],
    isLoading: false,
    loadingInitiator: null,
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
      requestEpochRef.current += 1;
    };
  }, [projectId]);

  const loadJobs = useCallback(
    (initiator: JobsLoadInitiator = "auto"): Promise<void> => {
      if (activeProjectIdRef.current !== projectId) return Promise.resolve();
      const activeRequest = controllerRef.current;
      if (activeRequest?.projectId === projectId && !activeRequest.controller.signal.aborted) {
        return activeRequest.promise;
      }
      const controller = new AbortController();
      const requestEpoch = ++requestEpochRef.current;
      setState((current) => ({
        projectId,
        jobs: current.projectId === projectId ? current.jobs : [],
        isLoading: true,
        loadingInitiator: initiator,
      }));

      const request: ActiveJobsRequest = {
        projectId,
        controller,
        promise: Promise.resolve(),
      };

      const isCurrentRequest = () =>
        !controller.signal.aborted &&
        requestEpochRef.current === requestEpoch &&
        activeProjectIdRef.current === projectId;

      request.promise = (async () => {
        try {
          const response = await api.jobs(projectId, { signal: controller.signal });
          if (!isCurrentRequest()) return;
          setState({
            projectId,
            jobs: response.jobs,
            isLoading: false,
            loadingInitiator: null,
          });
          setError(null);
        } catch (reason) {
          if (!isCurrentRequest()) return;
          setState((current) => ({
            projectId,
            jobs: current.projectId === projectId ? current.jobs : [],
            isLoading: false,
            loadingInitiator: null,
          }));
          setError(toErrorMessage(reason, "Unable to load jobs."));
        } finally {
          if (controllerRef.current === request) controllerRef.current = null;
        }
      })();
      controllerRef.current = request;
      return request.promise;
    },
    [projectId, setError],
  );

  const stateIsCurrent = state.projectId === projectId;
  const jobs = stateIsCurrent ? state.jobs : [];
  const isLoading = stateIsCurrent ? state.isLoading : false;
  const loadingInitiator = stateIsCurrent ? state.loadingInitiator : null;

  return { jobs, loadJobs, isLoading, loadingInitiator };
}
