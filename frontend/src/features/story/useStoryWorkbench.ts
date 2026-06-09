import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { api } from '@/app/api';
import type {
  WorkspaceSurfaceView,
} from '@/app/types/auth';
import type {
  JobOperation,
  JobStatus,
  ProviderName,
  ProviderStatus,
  WorkspaceCreateRequest,
  WorkspaceJob,
  WorkspaceJobRequest,
  WorkspaceStatus,
} from '@/app/types/story';

const TERMINAL_JOB_STATUSES = new Set<JobStatus>(['completed', 'failed', 'interrupted']);
const JOB_POLL_INTERVAL_MS = 1000;
const JOB_POLL_MAX_ATTEMPTS = 180;

export interface UseStoryWorkbenchResult {
  workspaces: WorkspaceStatus[];
  activeWorkspaceId: string | null;
  workspace: WorkspaceStatus | null;
  currentJob: WorkspaceJob | null;
  providers: ProviderStatus[];
  defaultProvider: ProviderName;
  isLoading: boolean;
  isBusy: boolean;
  error: string | null;
  refreshLibrary: () => Promise<void>;
  selectWorkspace: (workspaceId: string) => Promise<void>;
  createWorkspace: (payload: WorkspaceCreateRequest) => Promise<WorkspaceStatus>;
  runJob: (
    operation: JobOperation,
    payload?: Omit<WorkspaceJobRequest, 'operation'>,
  ) => Promise<WorkspaceJob>;
}

interface UseStoryWorkbenchOptions {
  authorId: string;
  enabled?: boolean;
  preferredWorkspaceId?: string | null;
  preferredJobId?: string | null;
  onSelectionChange?: (selection: {
    workspaceId: string | null;
    jobId: string | null;
    view: WorkspaceSurfaceView;
    workspace?: WorkspaceStatus | null;
  }) => void;
}

function formatError(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function isCancelledRequest(error: unknown): boolean {
  return error instanceof Error && error.message === 'Request cancelled.';
}

function delay(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(new Error('Request cancelled.'));
      return;
    }
    if (ms <= 0) {
      resolve();
      return;
    }
    let timeoutId = 0;
    const abortDelay = () => {
      window.clearTimeout(timeoutId);
      signal.removeEventListener('abort', abortDelay);
      reject(new Error('Request cancelled.'));
    };
    timeoutId = window.setTimeout(() => {
      window.clearTimeout(timeoutId);
      signal.removeEventListener('abort', abortDelay);
      resolve();
    }, ms);
    signal.addEventListener('abort', abortDelay, { once: true });
  });
}

function upsertWorkspace(
  workspaces: WorkspaceStatus[],
  nextWorkspace: WorkspaceStatus,
): WorkspaceStatus[] {
  const index = workspaces.findIndex(
    (workspace) => workspace.workspace_id === nextWorkspace.workspace_id,
  );
  if (index === -1) {
    return [nextWorkspace, ...workspaces];
  }

  const nextWorkspaces = [...workspaces];
  nextWorkspaces[index] = nextWorkspace;
  return nextWorkspaces;
}

function findWorkspaceJob(
  workspace: WorkspaceStatus,
  jobId: string,
): WorkspaceJob | null {
  return workspace.jobs.find((job) => job.job_id === jobId) ?? null;
}

function resolveWorkspaceJob(
  workspace: WorkspaceStatus,
  job: WorkspaceJob | null,
): WorkspaceJob | null {
  if (!job) {
    return workspace.jobs[0] ?? null;
  }

  const workspaceJob = findWorkspaceJob(workspace, job.job_id);
  if (!workspaceJob) {
    return job;
  }
  if (isTerminalJob(job) && !isTerminalJob(workspaceJob)) {
    return job;
  }
  return workspaceJob;
}

function isTerminalJob(job: WorkspaceJob): boolean {
  return TERMINAL_JOB_STATUSES.has(job.status);
}

export function useStoryWorkbench(
  authorIdOrOptions: string | UseStoryWorkbenchOptions,
): UseStoryWorkbenchResult {
  const {
    authorId,
    enabled = true,
    preferredWorkspaceId,
    preferredJobId,
    onSelectionChange,
  } =
    typeof authorIdOrOptions === 'string'
      ? { authorId: authorIdOrOptions }
      : authorIdOrOptions;
  const [workspaces, setWorkspaces] = useState<WorkspaceStatus[]>([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(null);
  const [workspace, setWorkspace] = useState<WorkspaceStatus | null>(null);
  const [currentJob, setCurrentJob] = useState<WorkspaceJob | null>(null);
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [defaultProvider, setDefaultProvider] = useState<ProviderName>('mock');
  const [isLoading, setIsLoading] = useState(true);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const activeWorkspaceIdRef = useRef<string | null>(null);
  const workspaceRef = useRef<WorkspaceStatus | null>(null);
  const preferredWorkspaceIdRef = useRef<string | null>(preferredWorkspaceId ?? null);
  const preferredJobIdRef = useRef<string | null>(preferredJobId ?? null);
  const onSelectionChangeRef = useRef(onSelectionChange);
  const pollControllerRef = useRef<AbortController | null>(null);
  const runTokenRef = useRef(0);

  useEffect(() => {
    activeWorkspaceIdRef.current = activeWorkspaceId;
  }, [activeWorkspaceId]);

  useEffect(() => {
    preferredWorkspaceIdRef.current = preferredWorkspaceId ?? null;
  }, [preferredWorkspaceId]);

  useEffect(() => {
    preferredJobIdRef.current = preferredJobId ?? null;
  }, [preferredJobId]);

  useEffect(() => {
    onSelectionChangeRef.current = onSelectionChange;
  }, [onSelectionChange]);

  useEffect(
    () => () => {
      pollControllerRef.current?.abort();
    },
    [],
  );

  const notifySelection = useCallback(
    (
      workspaceId: string | null,
      jobId: string | null,
      view: WorkspaceSurfaceView,
      workspace?: WorkspaceStatus | null,
    ) => {
      onSelectionChangeRef.current?.({
        workspaceId,
        jobId,
        view,
        workspace,
      });
    },
    [],
  );

  const cancelActivePoll = useCallback(() => {
    pollControllerRef.current?.abort();
    pollControllerRef.current = null;
    runTokenRef.current += 1;
  }, []);

  const pollJobToTerminal = useCallback(
    async (
      workspaceId: string,
      initialJob: WorkspaceJob,
      pollController: AbortController,
      isCurrentRun: () => boolean,
    ) => {
      let polledJob = initialJob;
      let terminalWorkspace: WorkspaceStatus | null = null;
      let lastPollError: unknown = null;

      for (let attempt = 0; attempt < JOB_POLL_MAX_ATTEMPTS; attempt += 1) {
        if (isTerminalJob(polledJob)) {
          break;
        }
        await delay(attempt === 0 ? 0 : JOB_POLL_INTERVAL_MS, pollController.signal);
        try {
          polledJob = await api.getWorkspaceJob(
            workspaceId,
            initialJob.job_id,
            { signal: pollController.signal },
          );
          lastPollError = null;
          if (isCurrentRun()) {
            setCurrentJob(polledJob);
          }
          if (!isTerminalJob(polledJob)) {
            const refreshedWorkspace = await api.getWorkspace(workspaceId, {
              signal: pollController.signal,
            });
            const workspaceJob = findWorkspaceJob(refreshedWorkspace, initialJob.job_id);
            if (workspaceJob) {
              polledJob = workspaceJob;
              lastPollError = null;
              if (isCurrentRun()) {
                setCurrentJob(workspaceJob);
              }
              if (isTerminalJob(workspaceJob)) {
                terminalWorkspace = refreshedWorkspace;
              }
            }
          }
        } catch (pollError) {
          if (isCancelledRequest(pollError)) {
            throw pollError;
          }
          lastPollError = pollError;
          const refreshedWorkspace = await api.getWorkspace(workspaceId, {
            signal: pollController.signal,
          }).catch((refreshError: unknown) => {
            if (isCancelledRequest(refreshError)) {
              throw refreshError;
            }
            lastPollError = refreshError;
            return null;
          });
          const workspaceJob = refreshedWorkspace
            ? findWorkspaceJob(refreshedWorkspace, initialJob.job_id)
            : null;
          if (workspaceJob) {
            polledJob = workspaceJob;
            lastPollError = null;
            if (isCurrentRun()) {
              setCurrentJob(workspaceJob);
            }
            if (isTerminalJob(workspaceJob)) {
              terminalWorkspace = refreshedWorkspace;
            }
          }
        }
      }

      if (!isTerminalJob(polledJob)) {
        if (lastPollError) {
          throw lastPollError;
        }
        throw new Error(`Job ${initialJob.job_id} did not finish before polling timed out.`);
      }

      const nextWorkspace =
        terminalWorkspace ??
        (await api.getWorkspace(workspaceId, {
          signal: pollController.signal,
        }));
      const resolvedJob = resolveWorkspaceJob(nextWorkspace, polledJob);
      return { nextWorkspace, resolvedJob, polledJob };
    },
    [],
  );

  const syncWorkspace = useCallback(
    (nextWorkspace: WorkspaceStatus, job: WorkspaceJob | null = null) => {
      setWorkspaces((current) => upsertWorkspace(current, nextWorkspace));
      setWorkspace(nextWorkspace);
      setActiveWorkspaceId(nextWorkspace.workspace_id);
      activeWorkspaceIdRef.current = nextWorkspace.workspace_id;
      workspaceRef.current = nextWorkspace;
      const nextJob = resolveWorkspaceJob(nextWorkspace, job);
      setCurrentJob(nextJob);
      notifySelection(
        nextWorkspace.workspace_id,
        nextJob?.job_id ?? null,
        nextJob ? 'playback' : 'workspace',
        nextWorkspace,
      );
    },
    [notifySelection],
  );

  const refreshLibrary = useCallback(async () => {
    if (!enabled) {
      setIsLoading(false);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const [providerResponse, response] = await Promise.all([
        api.listProviders(),
        api.listWorkspaces(),
      ]);
      setProviders(providerResponse.providers);
      setDefaultProvider(providerResponse.default_provider);
      setWorkspaces(response.workspaces);
      const selectedWorkspace =
        response.workspaces.find(
          (item) =>
            item.workspace_id === preferredWorkspaceIdRef.current ||
            item.workspace_id === activeWorkspaceIdRef.current,
        ) ?? response.workspaces[0] ?? null;

      if (!selectedWorkspace) {
        setWorkspace(null);
        setActiveWorkspaceId(null);
        activeWorkspaceIdRef.current = null;
        workspaceRef.current = null;
        setCurrentJob(null);
        notifySelection(null, null, 'workspace', null);
        return;
      }

      const preferredJob = preferredJobIdRef.current
        ? selectedWorkspace.jobs.find((job) => job.job_id === preferredJobIdRef.current)
        : null;
      syncWorkspace(selectedWorkspace, preferredJob);
    } catch (nextError) {
      setError(formatError(nextError, 'Unable to load local workspaces.'));
    } finally {
      setIsLoading(false);
    }
  }, [enabled, notifySelection, syncWorkspace]);

  useEffect(() => {
    void refreshLibrary();
  }, [authorId, enabled, refreshLibrary]);

  const selectWorkspace = useCallback(
    async (workspaceId: string) => {
      cancelActivePoll();
      setIsBusy(true);
      setError(null);
      try {
        const nextWorkspace = await api.getWorkspace(workspaceId);
        syncWorkspace(nextWorkspace, null);
      } catch (nextError) {
        setError(formatError(nextError, 'Unable to load the selected workspace.'));
        throw nextError;
      } finally {
        setIsBusy(false);
      }
    },
    [cancelActivePoll, syncWorkspace],
  );

  const createWorkspace = useCallback(
    async (payload: WorkspaceCreateRequest) => {
      cancelActivePoll();
      setIsBusy(true);
      setError(null);
      try {
        const nextWorkspace = await api.createWorkspace(payload);
        syncWorkspace(nextWorkspace, null);
        return nextWorkspace;
      } catch (nextError) {
        setError(formatError(nextError, 'Unable to create the workspace.'));
        throw nextError;
      } finally {
        setIsBusy(false);
      }
    },
    [cancelActivePoll, syncWorkspace],
  );

  const runJob = useCallback(
    async (
      operation: JobOperation,
      payload: Omit<WorkspaceJobRequest, 'operation'> = {},
    ) => {
      const workspaceId = activeWorkspaceIdRef.current;
      if (!workspaceId) {
        throw new Error('Create or select a workspace before running a job.');
      }

      setIsBusy(true);
      setError(null);
      pollControllerRef.current?.abort();
      const pollController = new AbortController();
      const runToken = runTokenRef.current + 1;
      runTokenRef.current = runToken;
      pollControllerRef.current = pollController;
      const isCurrentRun = () =>
        pollControllerRef.current === pollController && runTokenRef.current === runToken;
      try {
        const createdJob = await api.createWorkspaceJob(workspaceId, {
          ...payload,
          operation,
        });
        if (isCurrentRun()) {
          setCurrentJob(createdJob);
        }

        const { nextWorkspace, resolvedJob, polledJob } = await pollJobToTerminal(
          workspaceId,
          createdJob,
          pollController,
          isCurrentRun,
        );
        if (
          isCurrentRun() &&
          activeWorkspaceIdRef.current === workspaceId
        ) {
          syncWorkspace(nextWorkspace, resolvedJob);
        }
        return resolvedJob ?? polledJob;
      } catch (nextError) {
        if (isCancelledRequest(nextError)) {
          throw nextError;
        }
        setError(formatError(nextError, `Unable to run ${operation}.`));
        throw nextError;
      } finally {
        if (isCurrentRun()) {
          pollControllerRef.current = null;
          setIsBusy(false);
        }
      }
    },
    [pollJobToTerminal, syncWorkspace],
  );

  useEffect(() => {
    if (!enabled || !workspace || !currentJob || isTerminalJob(currentJob)) {
      return undefined;
    }
    if (pollControllerRef.current) {
      return undefined;
    }

    const workspaceId = workspace.workspace_id;
    const jobToResume = currentJob;
    const pollController = new AbortController();
    const runToken = runTokenRef.current + 1;
    runTokenRef.current = runToken;
    pollControllerRef.current = pollController;
    const isCurrentRun = () =>
      pollControllerRef.current === pollController && runTokenRef.current === runToken;

    setIsBusy(true);
    setError(null);

    void pollJobToTerminal(workspaceId, jobToResume, pollController, isCurrentRun)
      .then(({ nextWorkspace, resolvedJob }) => {
        if (
          isCurrentRun() &&
          activeWorkspaceIdRef.current === workspaceId
        ) {
          syncWorkspace(nextWorkspace, resolvedJob);
        }
      })
      .catch((nextError) => {
        if (isCancelledRequest(nextError)) {
          return;
        }
        setError(formatError(nextError, `Unable to poll ${jobToResume.operation}.`));
      })
      .finally(() => {
        if (isCurrentRun()) {
          pollControllerRef.current = null;
          setIsBusy(false);
        }
      });

    return () => {
      if (pollControllerRef.current === pollController) {
        pollController.abort();
      }
    };
  }, [
    currentJob?.job_id,
    enabled,
    pollJobToTerminal,
    syncWorkspace,
    workspace?.workspace_id,
  ]);

  return useMemo(
    () => ({
      workspaces,
      activeWorkspaceId,
      workspace,
      currentJob,
      providers,
      defaultProvider,
      isLoading,
      isBusy,
      error,
      refreshLibrary,
      selectWorkspace,
      createWorkspace,
      runJob,
    }),
    [
      activeWorkspaceId,
      createWorkspace,
      currentJob,
      defaultProvider,
      error,
      isBusy,
      isLoading,
      refreshLibrary,
      runJob,
      selectWorkspace,
      workspace,
      workspaces,
      providers,
    ],
  );
}
