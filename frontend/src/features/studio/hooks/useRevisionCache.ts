import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";

import type { RevisionSummary } from "@/app/types/studio";

import {
  activateRevisionOwner,
  getRevisionCacheStats,
  getRevisionCacheVersion,
  getRevisionOwnerState,
  type RevisionSubscriber,
  requestInitialRevisions,
  requestOlderRevisions,
  requestRevisionRefresh,
  resetRevisionCacheStore,
  revisionCacheKey,
  subscribeRevisionCache,
} from "./revisionCacheStore";

const noop = () => undefined;

interface RevisionCacheResult {
  readonly revisions: RevisionSummary[];
  readonly historyInitialized: boolean;
  readonly hasOlderRevisions: boolean;
  readonly isLoadingOlder: boolean;
  readonly isLoadingHistory: boolean;
  readonly refreshDocumentRevisions: (
    documentId: string,
    expectedRevisionId: string,
  ) => Promise<void>;
  readonly loadOlderRevisions: () => Promise<void>;
}

export function useRevisionCache(
  projectId: string,
  documentId: string | null,
  onError: (reason: unknown) => void,
  onSuccess: () => void = noop,
): RevisionCacheResult {
  useSyncExternalStore(subscribeRevisionCache, getRevisionCacheVersion, getRevisionCacheVersion);
  const key = documentId ? revisionCacheKey(projectId, documentId) : null;
  const ownerKeyRef = useRef<string | null>(null);
  const [subscriberToken] = useState(() => Symbol("revision-subscriber"));
  const subscriberRef = useRef<RevisionSubscriber>({ onError, onSuccess });
  subscriberRef.current.onError = onError;
  subscriberRef.current.onSuccess = onSuccess;

  useEffect(() => {
    if (key === null) return;
    ownerKeyRef.current = key;
    const deactivate = activateRevisionOwner(key, subscriberToken, subscriberRef.current);
    return () => {
      if (ownerKeyRef.current === key) ownerKeyRef.current = null;
      deactivate();
    };
  }, [key, subscriberToken]);

  useEffect(() => {
    if (documentId !== null) void requestInitialRevisions(projectId, documentId);
  }, [documentId, projectId]);

  const refreshDocumentRevisions = useCallback(
    (nextDocumentId: string, expectedRevisionId: string): Promise<void> => {
      if (ownerKeyRef.current !== revisionCacheKey(projectId, nextDocumentId)) {
        return Promise.resolve();
      }
      return requestRevisionRefresh(projectId, nextDocumentId, expectedRevisionId);
    },
    [projectId],
  );

  const loadOlderRevisions = useCallback((): Promise<void> => {
    if (documentId === null || ownerKeyRef.current !== key) return Promise.resolve();
    return requestOlderRevisions(projectId, documentId);
  }, [documentId, key, projectId]);
  const state = getRevisionOwnerState(key);

  return {
    revisions: state.revisions,
    historyInitialized: state.initialized,
    hasOlderRevisions: state.hasOlder,
    isLoadingOlder: state.isLoadingOlder,
    isLoadingHistory: state.isLoading,
    refreshDocumentRevisions,
    loadOlderRevisions,
  };
}

export const resetRevisionCacheForTests = resetRevisionCacheStore;
export const revisionCacheStatsForTests = getRevisionCacheStats;
