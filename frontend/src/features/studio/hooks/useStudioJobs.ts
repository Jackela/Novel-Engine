import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/app/api";
import type { StudioJobSummary } from "@/app/types/studio";

import { toErrorMessage } from "./toErrorMessage";

interface JobsState {
  readonly projectId: string;
  readonly jobs: StudioJobSummary[];
  readonly nextCursor: string | null;
  readonly isLoading: boolean;
  readonly loadingInitiator: JobsLoadInitiator | null;
}

export type JobsFreshLoadInitiator = "auto" | "refresh" | "retry" | "audit";
export type JobsLoadInitiator = JobsFreshLoadInitiator | "load_older";

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
  readonly kind: "fresh" | "older";
  readonly cursor: string | null;
  readonly controller: AbortController;
  promise: Promise<void>;
}

function emptyJobsState(projectId: string): JobsState {
  return {
    projectId,
    jobs: [],
    nextCursor: null,
    isLoading: false,
    loadingInitiator: null,
  };
}

function appendUniqueJobs(
  current: readonly StudioJobSummary[],
  older: readonly StudioJobSummary[],
): StudioJobSummary[] {
  const known = new Set(current.map((job) => job.id));
  const uniqueOlder = older.filter((job) => {
    if (known.has(job.id)) return false;
    known.add(job.id);
    return true;
  });
  return [...current, ...uniqueOlder];
}

export function useStudioJobs(
  projectId: string,
  setError: Dispatch<SetStateAction<string | null>>,
) {
  const activeProjectIdRef = useRef<string | null>(null);
  const controllerRef = useRef<ActiveJobsRequest | null>(null);
  const requestEpochRef = useRef(0);
  const [state, setState] = useState<JobsState>(() => emptyJobsState(projectId));
  const [proposalAuditState, setProposalAuditState] = useState<ProposalAuditState>(() => ({
    projectId,
    status: "idle",
  }));
  const proposalAuditStateRef = useRef(proposalAuditState);
  const proposalAuditEpochRef = useRef(0);

  useEffect(() => {
    activeProjectIdRef.current = projectId;
    setState((current) => (current.projectId === projectId ? current : emptyJobsState(projectId)));
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

  const publishProposalAuditStatus = useCallback(
    (status: ProposalAuditStatus): void => {
      const next = { projectId, status };
      proposalAuditStateRef.current = next;
      setProposalAuditState(next);
    },
    [projectId],
  );

  const startFreshRequest = useCallback(
    (initiator: JobsFreshLoadInitiator, audit: boolean): Promise<boolean> => {
      if (activeProjectIdRef.current !== projectId) return Promise.resolve(false);
      controllerRef.current?.controller.abort();
      const controller = new AbortController();
      const requestEpoch = ++requestEpochRef.current;
      if (audit) publishProposalAuditStatus("auditing");
      setState((current) => ({
        projectId,
        jobs: current.projectId === projectId ? current.jobs : [],
        nextCursor: current.projectId === projectId ? current.nextCursor : null,
        isLoading: true,
        loadingInitiator: initiator,
      }));

      const request: ActiveJobsRequest = {
        projectId,
        kind: "fresh",
        cursor: null,
        controller,
        promise: Promise.resolve(),
      };

      const isCurrentRequest = () =>
        !controller.signal.aborted &&
        requestEpochRef.current === requestEpoch &&
        activeProjectIdRef.current === projectId;

      const outcome = (async (): Promise<boolean> => {
        try {
          const response = await api.jobs(projectId, { signal: controller.signal });
          if (!isCurrentRequest()) return false;
          setState({
            projectId,
            jobs: response.jobs,
            nextCursor: response.next_cursor,
            isLoading: false,
            loadingInitiator: null,
          });
          if (audit) publishProposalAuditStatus("audit_succeeded");
          setError(null);
          return true;
        } catch (reason) {
          if (!isCurrentRequest()) return false;
          setState((current) => ({
            projectId,
            jobs: current.projectId === projectId ? current.jobs : [],
            nextCursor: current.projectId === projectId ? current.nextCursor : null,
            isLoading: false,
            loadingInitiator: null,
          }));
          if (audit) publishProposalAuditStatus("audit_failed");
          if (!audit) setError(toErrorMessage(reason, "Unable to load jobs."));
          return false;
        } finally {
          if (controllerRef.current === request) controllerRef.current = null;
        }
      })();
      request.promise = outcome.then(() => undefined);
      controllerRef.current = request;
      return outcome;
    },
    [projectId, publishProposalAuditStatus, setError],
  );

  const loadJobs = useCallback(
    (initiator: JobsFreshLoadInitiator = "auto"): Promise<void> =>
      startFreshRequest(initiator, false).then(() => undefined),
    [startFreshRequest],
  );

  const stateIsCurrent = state.projectId === projectId;
  const jobs = stateIsCurrent ? state.jobs : [];
  const nextCursor = stateIsCurrent ? state.nextCursor : null;
  const isLoading = stateIsCurrent ? state.isLoading : false;
  const loadingInitiator = stateIsCurrent ? state.loadingInitiator : null;
  const proposalAuditStatus =
    proposalAuditState.projectId === projectId ? proposalAuditState.status : "idle";

  const loadOlderJobs = useCallback((): Promise<void> => {
    if (activeProjectIdRef.current !== projectId || nextCursor === null) {
      return Promise.resolve();
    }
    const activeRequest = controllerRef.current;
    if (activeRequest && !activeRequest.controller.signal.aborted) {
      if (
        activeRequest.projectId === projectId &&
        activeRequest.kind === "older" &&
        activeRequest.cursor === nextCursor
      ) {
        return activeRequest.promise;
      }
      return Promise.resolve();
    }

    const controller = new AbortController();
    const requestEpoch = ++requestEpochRef.current;
    const request: ActiveJobsRequest = {
      projectId,
      kind: "older",
      cursor: nextCursor,
      controller,
      promise: Promise.resolve(),
    };
    const isCurrentRequest = () =>
      !controller.signal.aborted &&
      requestEpochRef.current === requestEpoch &&
      activeProjectIdRef.current === projectId;

    setState((current) => ({
      projectId,
      jobs: current.projectId === projectId ? current.jobs : [],
      nextCursor: current.projectId === projectId ? current.nextCursor : null,
      isLoading: true,
      loadingInitiator: "load_older",
    }));

    request.promise = (async () => {
      try {
        const response = await api.jobs(projectId, {
          cursor: nextCursor,
          signal: controller.signal,
        });
        if (!isCurrentRequest()) return;
        setState((current) => ({
          projectId,
          jobs:
            current.projectId === projectId
              ? appendUniqueJobs(current.jobs, response.jobs)
              : response.jobs,
          nextCursor: response.next_cursor,
          isLoading: false,
          loadingInitiator: null,
        }));
        setError(null);
      } catch (reason) {
        if (!isCurrentRequest()) return;
        setState((current) => ({
          projectId,
          jobs: current.projectId === projectId ? current.jobs : [],
          nextCursor: current.projectId === projectId ? current.nextCursor : null,
          isLoading: false,
          loadingInitiator: null,
        }));
        setError(toErrorMessage(reason, "Unable to load older jobs."));
      } finally {
        if (controllerRef.current === request) controllerRef.current = null;
      }
    })();
    controllerRef.current = request;
    return request.promise;
  }, [nextCursor, projectId, setError]);

  const auditProposalOutcome = useCallback(async (): Promise<boolean> => {
    if (activeProjectIdRef.current !== projectId) return false;
    proposalAuditEpochRef.current += 1;
    return startFreshRequest("audit", true);
  }, [projectId, startFreshRequest]);

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
    loadOlderJobs,
    hasOlderJobs: nextCursor !== null,
    isLoading,
    loadingInitiator,
    proposalAuditStatus,
    auditProposalOutcome,
    clearProposalAudit,
    proposalAuditEpoch,
    isProposalAuditGated,
  };
}
