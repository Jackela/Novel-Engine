import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { DocumentSummary, StudioDocument } from "@/app/types/studio";

import { runCurrentDocumentReadCycle } from "./currentDocumentReadCycle";
import {
  acquireCurrentDocumentRead,
  type CurrentDocumentReadKey,
} from "./currentDocumentReadRegistry";
import type { ProjectShellReadAuthority } from "./projectShellReadAuthority";

const SHELL_CHANGED_ERROR = "The project changed while loading this document. Please retry.";

interface CurrentDocumentState {
  readonly key: CurrentDocumentReadKey | null;
  readonly document: StudioDocument | null;
  readonly error: string | null;
  readonly isLoading: boolean;
  readonly attempt: number;
  readonly completed: boolean;
}

interface UseCurrentDocumentOptions extends ProjectShellReadAuthority {
  readonly summary: DocumentSummary | null;
  readonly lifecycle: symbol;
  readonly onSessionLoss: () => void;
  readonly onProjectMissing: () => void;
}

function sameKey(left: CurrentDocumentReadKey | null, right: CurrentDocumentReadKey | null) {
  return (
    left === right ||
    (left !== null &&
      right !== null &&
      left.projectId === right.projectId &&
      left.documentId === right.documentId &&
      left.expectedRevisionId === right.expectedRevisionId &&
      left.lifecycle === right.lifecycle)
  );
}

export function useCurrentDocument(
  projectId: string,
  {
    summary,
    lifecycle,
    captureProjectShellRead,
    publishProjectShellRead,
    onSessionLoss,
    onProjectMissing,
  }: UseCurrentDocumentOptions,
) {
  const [retryEpoch, setRetryEpoch] = useState(0);
  const [state, setState] = useState<CurrentDocumentState>({
    key: null,
    document: null,
    error: null,
    isLoading: summary !== null,
    attempt: 0,
    completed: false,
  });
  const stateRef = useRef(state);
  const cycleRef = useRef<symbol | null>(null);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  const summaryProjectId = summary?.project_id ?? null;
  const summaryDocumentId = summary?.id ?? null;
  const summaryRevisionId = summary?.current_revision_id ?? null;
  const key = useMemo<CurrentDocumentReadKey | null>(
    () =>
      summaryProjectId === projectId && summaryDocumentId !== null && summaryRevisionId !== null
        ? {
            projectId,
            documentId: summaryDocumentId,
            expectedRevisionId: summaryRevisionId,
            lifecycle,
          }
        : null,
    [lifecycle, projectId, summaryDocumentId, summaryProjectId, summaryRevisionId],
  );

  useEffect(() => {
    if (key === null) {
      cycleRef.current = null;
      setState({
        key: null,
        document: null,
        error: null,
        isLoading: false,
        attempt: retryEpoch,
        completed: true,
      });
      return;
    }
    const accepted = stateRef.current;
    if (sameKey(accepted.key, key) && accepted.completed && accepted.attempt === retryEpoch) {
      return;
    }

    const cycle = Symbol(`current document read ${retryEpoch}`);
    cycleRef.current = cycle;
    setState({
      key,
      document: null,
      error: null,
      isLoading: true,
      attempt: retryEpoch,
      completed: false,
    });
    const authority = { captureProjectShellRead, publishProjectShellRead };
    const lease = acquireCurrentDocumentRead(key, (signal) =>
      runCurrentDocumentReadCycle(key, authority, signal),
    );
    let released = false;
    const isCurrent = () => !released && cycleRef.current === cycle;
    const publishFailure = (message: string, failureKey = key) => {
      if (isCurrent())
        setState({
          key: failureKey,
          document: null,
          error: message,
          isLoading: false,
          attempt: retryEpoch,
          completed: true,
        });
    };

    void lease.promise.then(
      (outcome) => {
        if (!isCurrent()) return;
        if (outcome.status === "session-lost") {
          onSessionLoss();
          return;
        }
        if (outcome.status === "project-missing") {
          onProjectMissing();
          return;
        }
        if ("commitShell" in outcome && outcome.commitShell && !outcome.commitShell()) {
          publishFailure(SHELL_CHANGED_ERROR);
          return;
        }
        switch (outcome.status) {
          case "document":
            setState({
              key: outcome.key,
              document: outcome.document,
              error: null,
              isLoading: false,
              attempt: retryEpoch,
              completed: true,
            });
            return;
          case "missing":
            setState({
              key,
              document: null,
              error: null,
              isLoading: false,
              attempt: retryEpoch,
              completed: true,
            });
            return;
          case "failure":
            publishFailure(outcome.message, outcome.key ?? key);
        }
      },
      () => undefined,
    );

    return () => {
      released = true;
      lease.release();
      if (cycleRef.current === cycle) cycleRef.current = null;
    };
  }, [
    captureProjectShellRead,
    key,
    onProjectMissing,
    onSessionLoss,
    publishProjectShellRead,
    retryEpoch,
  ]);

  const visible = sameKey(state.key, key)
    ? state
    : {
        key,
        document: null,
        error: null,
        isLoading: key !== null,
        attempt: retryEpoch,
        completed: false,
      };
  const retry = useCallback(() => {
    setRetryEpoch((current) => current + 1);
  }, []);

  return {
    document: visible.document,
    error: visible.error,
    isLoading: visible.isLoading,
    retry,
  };
}
