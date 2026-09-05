import { useCallback } from "react";

import { api } from "@/app/api";
import type { ExportsPage } from "@/app/apiWorkflowContract";

import {
  appendUniqueById,
  mergeRefreshedKeysetFirstPage,
  useKeysetOlderPages,
} from "./keysetHistory";
import { useLazyInspectorResource } from "./useLazyInspectorResource";

interface UseExportHistoryOptions {
  readonly active: boolean;
  readonly projectId: string;
  readonly recheckProject: (signal: AbortSignal) => Promise<boolean>;
  readonly onSessionLost: () => void;
}

const EMPTY_PAGE: ExportsPage = { exports: [], next_cursor: null };

/**
 * Merge one cursorless first-page refresh (#460): prepend and de-duplicate
 * new summaries, preserve a loaded contiguous older tail and its
 * continuation, and replace the cache when the fresh page exposes an
 * unknown gap instead of splicing across it.
 */
export function mergeRefreshedFirstPage(current: ExportsPage, refreshed: ExportsPage): ExportsPage {
  const merged = mergeRefreshedKeysetFirstPage(
    current.exports,
    current.next_cursor,
    refreshed.exports,
    refreshed.next_cursor,
    (item) => item.id,
  );
  return { exports: merged.items, next_cursor: merged.nextCursor };
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
  const nextCursor = resource.initialized ? resource.data.next_cursor : null;
  const olderPages = useKeysetOlderPages<ExportsPage>({
    cleanupKey: projectId,
    isEnabled: () => active,
    nextCursor,
    fetchPage: (cursor, signal) => api.exports(projectId, { cursor, signal }),
    commitPage: (page) =>
      setData((current) => ({
        exports: appendUniqueById(current.exports, page.exports, (item) => item.id),
        next_cursor: page.next_cursor,
      })),
    busyErrorMessage: "Unable to load older exports.",
  });

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
    olderError: olderPages.olderError,
    hasOlderExports: nextCursor !== null,
    isLoadingOlderExports: olderPages.isLoadingOlder,
    onRetryHistory: resource.retry,
    onLoadOlderExports: olderPages.loadOlder,
    applyRefreshedFirstPage,
  };
}
