import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/app/api";
import type { JobsPage } from "@/app/apiWorkflowContract";
import type { StudioJobSummary } from "@/app/types/studio";

import { appendUniqueById, useKeysetOlderPages } from "./keysetHistory";
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

/** The single in-flight first-page read that owns the jobs surface. */
interface ActiveJobsRequest {
  readonly projectId: string;
  readonly controller: AbortController;
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

  const stateIsCurrent = state.projectId === projectId;
  const jobs = stateIsCurrent ? state.jobs : [];
  const nextCursor = stateIsCurrent ? state.nextCursor : null;

  // The older traversal shares the surface's single-flight rule: it waits
  // while a first-page read owns the surface, and a first-page read preempts
  // it through abortInFlight.
  const olderPages = useKeysetOlderPages<JobsPage>({
    cleanupKey: projectId,
    isEnabled: () => activeProjectIdRef.current === projectId,
    isBlocked: () => {
      const active = controllerRef.current;
      return active !== null && !active.controller.signal.aborted;
    },
    nextCursor,
    fetchPage: (cursor, signal) => api.jobs(projectId, { cursor, signal }),
    commitPage: (page) =>
      setState((current) => ({
        projectId,
        jobs:
          current.projectId === projectId
            ? appendUniqueById(current.jobs, page.jobs, (job) => job.id)
            : page.jobs,
        nextCursor: page.next_cursor,
        isLoading: false,
        loadingInitiator: null,
      })),
    onOutcome: (error) => setError(error),
    busyErrorMessage: "Unable to load older jobs.",
  });
  const abortInFlightOlder = olderPages.abortInFlight;

  const startFreshRequest = useCallback(
    (initiator: JobsFreshLoadInitiator, audit: boolean): Promise<boolean> => {
      if (activeProjectIdRef.current !== projectId) return Promise.resolve(false);
      abortInFlightOlder();
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

      const request: ActiveJobsRequest = { projectId, controller };

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
      controllerRef.current = request;
      return outcome;
    },
    [abortInFlightOlder, projectId, publishProposalAuditStatus, setError],
  );

  const loadJobs = useCallback(
    (initiator: JobsFreshLoadInitiator = "auto"): Promise<void> =>
      startFreshRequest(initiator, false).then(() => undefined),
    [startFreshRequest],
  );

  const proposalAuditStatus =
    proposalAuditState.projectId === projectId ? proposalAuditState.status : "idle";

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

  const isLoading = stateIsCurrent && (state.isLoading || olderPages.isLoadingOlder);
  const loadingInitiator = !stateIsCurrent
    ? null
    : state.isLoading
      ? state.loadingInitiator
      : olderPages.isLoadingOlder
        ? "load_older"
        : null;

  return {
    jobs,
    loadJobs,
    loadOlderJobs: olderPages.loadOlder,
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
