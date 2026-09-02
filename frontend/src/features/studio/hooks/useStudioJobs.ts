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

export type JobsLoadInitiator = "auto" | "refresh" | "retry" | "audit";

export type ProposalAuditStatus = "idle" | "auditing" | "audit_failed" | "audit_succeeded";

export interface ProposalAuditControl {
  readonly status: ProposalAuditStatus;
  readonly audit: () => Promise<boolean>;
  readonly clear: () => void;
  /** Monotonic project-lifecycle marker; clearing UI state never rewinds it. */
  readonly epoch: () => number;
  /** Synchronous admission check, including the render before React publishes state. */
  readonly isGated: () => boolean;
}

interface ProposalAuditState {
  readonly projectId: string;
  readonly status: ProposalAuditStatus;
}

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
  const [proposalAuditState, setProposalAuditState] = useState<ProposalAuditState>(() => ({
    projectId,
    status: "idle",
  }));
  const proposalAuditStateRef = useRef(proposalAuditState);
  const proposalAuditEpochRef = useRef(0);

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
      if (
        proposalAuditStateRef.current.projectId === projectId &&
        proposalAuditStateRef.current.status === "auditing"
      ) {
        const retryable = { projectId, status: "audit_failed" } as const;
        proposalAuditStateRef.current = retryable;
        setProposalAuditState(retryable);
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
  const proposalAuditStatus =
    proposalAuditState.projectId === projectId ? proposalAuditState.status : "idle";

  const publishProposalAuditStatus = useCallback(
    (status: ProposalAuditStatus): void => {
      const next = { projectId, status };
      proposalAuditStateRef.current = next;
      setProposalAuditState(next);
    },
    [projectId],
  );

  const auditProposalOutcome = useCallback(async (): Promise<boolean> => {
    if (activeProjectIdRef.current !== projectId) return false;
    proposalAuditEpochRef.current += 1;
    controllerRef.current?.controller.abort();

    const controller = new AbortController();
    const requestEpoch = ++requestEpochRef.current;
    publishProposalAuditStatus("auditing");
    setState((current) => ({
      projectId,
      jobs: current.projectId === projectId ? current.jobs : [],
      isLoading: true,
      loadingInitiator: "audit",
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

    const auditPromise = (async (): Promise<boolean> => {
      try {
        const response = await api.jobs(projectId, { signal: controller.signal });
        if (!isCurrentRequest()) return false;
        setState({
          projectId,
          jobs: response.jobs,
          isLoading: false,
          loadingInitiator: null,
        });
        publishProposalAuditStatus("audit_succeeded");
        setError(null);
        return true;
      } catch {
        if (!isCurrentRequest()) return false;
        setState((current) => ({
          projectId,
          jobs: current.projectId === projectId ? current.jobs : [],
          isLoading: false,
          loadingInitiator: null,
        }));
        publishProposalAuditStatus("audit_failed");
        return false;
      } finally {
        if (controllerRef.current === request) controllerRef.current = null;
      }
    })();
    request.promise = auditPromise.then(() => undefined);
    controllerRef.current = request;
    return auditPromise;
  }, [projectId, publishProposalAuditStatus, setError]);

  const clearProposalAudit = useCallback(() => {
    if (activeProjectIdRef.current !== projectId) return;
    publishProposalAuditStatus("idle");
  }, [projectId, publishProposalAuditStatus]);
  const proposalAuditEpoch = useCallback(() => proposalAuditEpochRef.current, []);
  const isProposalAuditGated = useCallback(() => {
    const current = proposalAuditStateRef.current;
    return (
      current.projectId === projectId &&
      (current.status === "auditing" || current.status === "audit_failed")
    );
  }, [projectId]);

  return {
    jobs,
    loadJobs,
    isLoading,
    loadingInitiator,
    proposalAuditStatus,
    auditProposalOutcome,
    clearProposalAudit,
    proposalAuditEpoch,
    isProposalAuditGated,
  };
}
