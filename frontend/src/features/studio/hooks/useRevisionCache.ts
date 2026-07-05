import { useCallback, useEffect, useRef, useSyncExternalStore } from 'react';

import { api } from '@/app/api';
import type { Revision } from '@/app/types/studio';

const emptyRevisions: Revision[] = [];
const revisionCache = new Map<string, Revision[]>();
const listeners = new Set<() => void>();
let revisionStoreVersion = 0;

interface RevisionCacheResult {
  readonly revisions: Revision[];
  readonly refreshDocumentRevisions: (documentId: string) => void;
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
): RevisionCacheResult {
  const requestIds = useRef<Map<string, number> | null>(null);
  useSyncExternalStore(subscribeRevisionStore, getRevisionStoreSnapshot, getRevisionStoreSnapshot);

  const refreshDocumentRevisions = useCallback(
    (nextDocumentId: string) => {
      let currentRequestIds = requestIds.current;
      if (currentRequestIds === null) {
        currentRequestIds = new Map<string, number>();
        requestIds.current = currentRequestIds;
      }
      const key = cacheKey(projectId, nextDocumentId);
      const requestId = (currentRequestIds.get(key) ?? 0) + 1;
      currentRequestIds.set(key, requestId);
      void api
        .revisions(projectId, nextDocumentId)
        .then((response) => {
          if (requestIds.current?.get(key) !== requestId) return;
          replaceCachedRevisions(projectId, nextDocumentId, response.revisions);
        })
        .catch((reason: unknown) => {
          if (requestIds.current?.get(key) !== requestId) return;
          onError(reason);
        });
    },
    [onError, projectId],
  );

  useEffect(() => {
    if (documentId === null) return;
    replaceCachedRevisions(projectId, documentId, emptyRevisions);
    refreshDocumentRevisions(documentId);
  }, [documentId, projectId, refreshDocumentRevisions]);

  return {
    revisions: revisionsFor(projectId, documentId),
    refreshDocumentRevisions,
  };
}
