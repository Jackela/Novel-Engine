import { useCallback, useEffect, useRef, useSyncExternalStore } from "react";

import { api } from "@/app/api";
import type { Revision } from "@/app/types/studio";

const emptyRevisions: Revision[] = [];
const revisionCache = new Map<string, Revision[]>();
const revisionRequestVersions = new Map<string, number>();
const listeners = new Set<() => void>();
let revisionStoreVersion = 0;
const noop = () => undefined;

interface RevisionCacheResult {
  readonly revisions: Revision[];
  readonly refreshDocumentRevisions: (documentId: string) => Promise<void>;
}

interface ActiveRevisionRequest {
  readonly controller: AbortController;
  readonly key: string;
  readonly lifecycleEpoch: number;
  readonly requestVersion: number;
}

function cacheKey(projectId: string, documentId: string): string {
  return `${projectId}\u0000${documentId}`;
}

function emitRevisionStoreChange(): void {
  revisionStoreVersion += 1;
  for (const listener of listeners) {
    listener();
  }
}

function subscribeRevisionStore(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getRevisionStoreSnapshot(): number {
  return revisionStoreVersion;
}

function revisionsFor(projectId: string, documentId: string | null): Revision[] {
  return documentId
    ? (revisionCache.get(cacheKey(projectId, documentId)) ?? emptyRevisions)
    : emptyRevisions;
}

function replaceCachedRevisions(
  projectId: string,
  documentId: string,
  revisions: Revision[],
): void {
  revisionCache.set(cacheKey(projectId, documentId), revisions);
  emitRevisionStoreChange();
}

export function useRevisionCache(
  projectId: string,
  documentId: string | null,
  onError: (reason: unknown) => void,
  onSuccess: () => void = noop,
): RevisionCacheResult {
  useSyncExternalStore(subscribeRevisionStore, getRevisionStoreSnapshot, getRevisionStoreSnapshot);
  const ownerKey = documentId ? cacheKey(projectId, documentId) : `${projectId}\u0000`;
  const ownerKeyRef = useRef<string | null>(null);
  const lifecycleEpochRef = useRef(0);
  const activeRequestRef = useRef<ActiveRevisionRequest | null>(null);

  useEffect(() => {
    const lifecycleOwnerKey = ownerKey;
    const lifecycleEpoch = lifecycleEpochRef.current + 1;
    ownerKeyRef.current = lifecycleOwnerKey;
    lifecycleEpochRef.current = lifecycleEpoch;
    return () => {
      if (ownerKeyRef.current === lifecycleOwnerKey) {
        ownerKeyRef.current = null;
      }
      if (lifecycleEpochRef.current === lifecycleEpoch) {
        lifecycleEpochRef.current += 1;
      }
      const activeRequest = activeRequestRef.current;
      if (activeRequest?.key === lifecycleOwnerKey) {
        activeRequestRef.current = null;
        activeRequest.controller.abort();
      }
    };
  }, [ownerKey]);

  const refreshDocumentRevisions = useCallback(
    async (nextDocumentId: string): Promise<void> => {
      const key = cacheKey(projectId, nextDocumentId);
      if (ownerKeyRef.current !== key) return;
      activeRequestRef.current?.controller.abort();
      const controller = new AbortController();
      const lifecycleEpoch = lifecycleEpochRef.current;
      const requestVersion = (revisionRequestVersions.get(key) ?? 0) + 1;
      revisionRequestVersions.set(key, requestVersion);
      const request: ActiveRevisionRequest = {
        controller,
        key,
        lifecycleEpoch,
        requestVersion,
      };
      activeRequestRef.current = request;
      const isCurrentRequest = (): boolean =>
        !controller.signal.aborted &&
        ownerKeyRef.current === key &&
        lifecycleEpochRef.current === request.lifecycleEpoch &&
        activeRequestRef.current === request &&
        revisionRequestVersions.get(key) === request.requestVersion;
      try {
        const response = await api.revisions(projectId, nextDocumentId, {
          signal: controller.signal,
        });
        if (isCurrentRequest()) {
          replaceCachedRevisions(projectId, nextDocumentId, response.revisions);
          onSuccess();
        }
      } catch (reason: unknown) {
        if (isCurrentRequest()) {
          onError(reason);
        }
      } finally {
        if (activeRequestRef.current === request) {
          activeRequestRef.current = null;
        }
      }
    },
    [onError, onSuccess, projectId],
  );

  useEffect(() => {
    if (documentId === null) return;
    replaceCachedRevisions(projectId, documentId, emptyRevisions);
    void refreshDocumentRevisions(documentId);
  }, [documentId, projectId, refreshDocumentRevisions]);

  return {
    revisions: revisionsFor(projectId, documentId),
    refreshDocumentRevisions,
  };
}
