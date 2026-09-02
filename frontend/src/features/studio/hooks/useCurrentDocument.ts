import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { api, HttpError } from "@/app/api";
import type { DocumentSummary, ProjectShell, StudioDocument } from "@/app/types/studio";

import {
  acquireCurrentDocumentRead,
  type CurrentDocumentReadKey,
} from "./currentDocumentReadRegistry";
import { toErrorMessage } from "./toErrorMessage";

const DEFAULT_ERROR = "Unable to load this document. Please retry.";
const CHURN_ERROR = "This document changed again while loading. Please retry.";
const INCONSISTENT_ERROR = "This document is listed but could not be loaded. Please retry.";

interface CurrentDocumentState {
  readonly key: CurrentDocumentReadKey | null;
  readonly document: StudioDocument | null;
  readonly error: string | null;
  readonly isLoading: boolean;
}

interface ConvergenceGuard {
  readonly projectId: string;
  readonly documentId: string;
  readonly replacementRevisionId: string;
}

interface UseCurrentDocumentOptions {
  readonly summary: DocumentSummary | null;
  readonly lifecycle: symbol;
  readonly setProject: Dispatch<SetStateAction<ProjectShell | null>>;
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

function summaryIn(shell: ProjectShell, documentId: string): DocumentSummary | null {
  return shell.documents.find((document) => document.id === documentId) ?? null;
}

export function useCurrentDocument(
  projectId: string,
  { summary, lifecycle, setProject, onSessionLoss, onProjectMissing }: UseCurrentDocumentOptions,
) {
  const [retryEpoch, setRetryEpoch] = useState(0);
  const [state, setState] = useState<CurrentDocumentState>({
    key: null,
    document: null,
    error: null,
    isLoading: summary !== null,
  });
  const stateRef = useRef(state);
  const cycleRef = useRef<symbol | null>(null);
  const convergenceRef = useRef<ConvergenceGuard | null>(null);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  const key = useMemo<CurrentDocumentReadKey | null>(
    () =>
      summary
        ? {
            projectId,
            documentId: summary.id,
            expectedRevisionId: summary.current_revision_id,
            lifecycle,
          }
        : null,
    [lifecycle, projectId, summary],
  );

  useEffect(() => {
    if (key === null) {
      cycleRef.current = null;
      convergenceRef.current = null;
      setState({ key: null, document: null, error: null, isLoading: false });
      return;
    }
    const accepted = stateRef.current;
    if (
      sameKey(accepted.key, key) &&
      accepted.document?.current_revision_id === key.expectedRevisionId
    ) {
      return;
    }

    const cycle = Symbol(`current document read ${retryEpoch}`);
    cycleRef.current = cycle;
    setState({ key, document: null, error: null, isLoading: true });
    const lease = acquireCurrentDocumentRead(key);
    let released = false;
    const isCurrent = () => !released && cycleRef.current === cycle;
    const publishFailure = (message: string, failureKey = key) => {
      if (isCurrent())
        setState({ key: failureKey, document: null, error: message, isLoading: false });
    };

    const refreshShell = async (): Promise<ProjectShell | null> => {
      try {
        const refreshed = await api.project(projectId);
        if (!isCurrent()) return null;
        setProject((current) => (isCurrent() && current?.id === projectId ? refreshed : current));
        return refreshed;
      } catch (reason) {
        if (!isCurrent()) return null;
        if (reason instanceof HttpError && reason.status === 401) {
          onSessionLoss();
          return null;
        }
        if (reason instanceof HttpError && reason.status === 404) {
          onProjectMissing();
          return null;
        }
        publishFailure(toErrorMessage(reason, DEFAULT_ERROR));
        return null;
      }
    };

    void lease.promise.then(
      async (document) => {
        if (!isCurrent()) return;
        if (document.project_id !== key.projectId || document.id !== key.documentId) {
          publishFailure(INCONSISTENT_ERROR);
          return;
        }
        if (document.current_revision_id === key.expectedRevisionId) {
          convergenceRef.current = null;
          setState({ key, document, error: null, isLoading: false });
          return;
        }

        const guard = convergenceRef.current;
        if (
          guard?.projectId === projectId &&
          guard.documentId === key.documentId &&
          guard.replacementRevisionId === key.expectedRevisionId
        ) {
          convergenceRef.current = null;
          publishFailure(CHURN_ERROR);
          return;
        }

        const refreshed = await refreshShell();
        if (!refreshed || !isCurrent()) return;
        const freshSummary = summaryIn(refreshed, key.documentId);
        if (!freshSummary) {
          convergenceRef.current = null;
          return;
        }
        const freshKey = { ...key, expectedRevisionId: freshSummary.current_revision_id };
        if (document.current_revision_id === freshSummary.current_revision_id) {
          convergenceRef.current = null;
          setState({ key: freshKey, document, error: null, isLoading: false });
          return;
        }
        convergenceRef.current = {
          projectId,
          documentId: key.documentId,
          replacementRevisionId: freshSummary.current_revision_id,
        };
        setState({ key: freshKey, document: null, error: null, isLoading: true });
      },
      async (reason) => {
        if (!isCurrent()) return;
        if (reason instanceof HttpError && reason.status === 401) {
          onSessionLoss();
          return;
        }
        if (reason instanceof HttpError && reason.status === 404) {
          const refreshed = await refreshShell();
          if (!refreshed || !isCurrent()) return;
          if (summaryIn(refreshed, key.documentId)) publishFailure(INCONSISTENT_ERROR);
          return;
        }
        publishFailure(toErrorMessage(reason, DEFAULT_ERROR));
      },
    );

    return () => {
      released = true;
      lease.release();
      if (cycleRef.current === cycle) cycleRef.current = null;
    };
  }, [key, onProjectMissing, onSessionLoss, projectId, retryEpoch, setProject]);

  const visible = sameKey(state.key, key)
    ? state
    : { key, document: null, error: null, isLoading: key !== null };
  const retry = useCallback(() => {
    convergenceRef.current = null;
    setRetryEpoch((current) => current + 1);
  }, []);

  return {
    document: visible.document,
    error: visible.error,
    isLoading: visible.isLoading,
    retry,
  };
}
