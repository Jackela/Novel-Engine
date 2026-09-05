import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/app/api";
import type { ExportsPage } from "@/app/apiWorkflowContract";
import type { StudioExport } from "@/app/types/studio";

import { toErrorMessage } from "./toErrorMessage";
import { useLazyInspectorResource } from "./useLazyInspectorResource";

interface UseExportHistoryOptions {
  readonly active: boolean;
  readonly projectId: string;
  readonly recheckProject: (signal: AbortSignal) => Promise<boolean>;
  readonly onSessionLost: () => void;
}

interface ActiveOlderRequest {
  readonly projectId: string;
  readonly cursor: string;
  readonly controller: AbortController;
  promise: Promise<void>;
}

const EMPTY_PAGE: ExportsPage = { exports: [], next_cursor: null };

function appendUniqueExports(
  current: readonly StudioExport[],
  older: readonly StudioExport[],
): StudioExport[] {
  const known = new Set(current.map((item) => item.id));
  const uniqueOlder = older.filter((item) => {
    if (known.has(item.id)) return false;
    known.add(item.id);
    return true;
  });
  return [...current, ...uniqueOlder];
}

/**
 * Merge one cursorless first-page refresh (#460): prepend and de-duplicate
 * new summaries, preserve a loaded contiguous older tail and its
 * continuation, and replace the cache when the fresh page exposes an
 * unknown gap instead of splicing across it.
 */
export function mergeRefreshedFirstPage(current: ExportsPage, refreshed: ExportsPage): ExportsPage {
  if (current.exports.length === 0 || refreshed.next_cursor === null) return refreshed;
  const refreshedIds = new Set(refreshed.exports.map((item) => item.id));
  const hasOverlap = current.exports.some((item) => refreshedIds.has(item.id));
  if (!hasOverlap) return refreshed;
  return {
    exports: [
      ...refreshed.exports,
      ...current.exports.filter((item) => !refreshedIds.has(item.id)),
    ],
    next_cursor: current.next_cursor,
  };
}

/**
 * One URL-selected Export history: a bounded first page plus explicit
 * older-page traversal and a bounded post-export first-page refresh.
 */
export function useExportHistory({
  active,
  projectId,
  recheckProject,
  onSessionLost,
}: UseExportHistoryOptions) {
  const requestExports = useCallback(
    async (signal: AbortSignal) => api.exports(projectId, { signal }),
    [projectId],
  );
  const resource = useLazyInspectorResource<ExportsPage>({
    active,
    projectId,
    empty: EMPTY_PAGE,
    request: requestExports,
    recheckProject,
    onSessionLost,
    missingResourceMessage: "Export history is unavailable for this project.",
    loadErrorMessage: "Unable to load export history.",
  });
  const setData = resource.setData;
  const activeOlderRef = useRef<ActiveOlderRequest | null>(null);
  const [olderBusy, setOlderBusy] = useState(false);
  const [olderError, setOlderError] = useState<string | null>(null);

  useEffect(() => {
    const owningProjectId = projectId;
    return () => {
      // A project change or unmount aborts only the older request this
      // owner started; late responses cannot publish into another owner.
      const request = activeOlderRef.current;
      if (request === null || request.projectId !== owningProjectId) return;
      activeOlderRef.current = null;
      request.controller.abort();
      setOlderBusy(false);
    };
  }, [projectId]);

  const nextCursor = resource.initialized ? resource.data.next_cursor : null;
  const loadOlderExports = useCallback((): Promise<void> => {
    if (!active || nextCursor === null) return Promise.resolve();
    const inFlight = activeOlderRef.current;
    if (inFlight && !inFlight.controller.signal.aborted) {
      return inFlight.projectId === projectId && inFlight.cursor === nextCursor
        ? inFlight.promise
        : Promise.resolve();
    }
    const controller = new AbortController();
    const request: ActiveOlderRequest = {
      projectId,
      cursor: nextCursor,
      controller,
      promise: Promise.resolve(),
    };
    setOlderBusy(true);
    request.promise = (async () => {
      try {
        const page = await api.exports(projectId, {
          cursor: nextCursor,
          signal: controller.signal,
        });
        if (activeOlderRef.current !== request || controller.signal.aborted) return;
        activeOlderRef.current = null;
        setOlderBusy(false);
        setData((current) => ({
          exports: appendUniqueExports(current.exports, page.exports),
          next_cursor: page.next_cursor,
        }));
        setOlderError(null);
      } catch (reason) {
        if (activeOlderRef.current !== request || controller.signal.aborted) return;
        activeOlderRef.current = null;
        setOlderBusy(false);
        setOlderError(toErrorMessage(reason, "Unable to load older exports."));
      }
    })();
    activeOlderRef.current = request;
    return request.promise;
  }, [active, nextCursor, projectId, setData]);

  const applyRefreshedFirstPage = useCallback(
    (page: ExportsPage): void => {
      setData((current) => mergeRefreshedFirstPage(current, page));
    },
    [setData],
  );

  return {
    exports: resource.data.exports,
    historyInitialized: resource.initialized,
    isLoadingHistory: resource.isLoading,
    historyError: resource.error,
    olderError,
    hasOlderExports: nextCursor !== null,
    isLoadingOlderExports: olderBusy,
    onRetryHistory: resource.retry,
    onLoadOlderExports: loadOlderExports,
    applyRefreshedFirstPage,
  };
}
