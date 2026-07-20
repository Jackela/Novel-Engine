import { useCallback, useEffect, useSyncExternalStore } from 'react';

import { api } from '@/app/api';
import type { Revision } from '@/app/types/studio';

const emptyRevisions: Revision[] = [];
const revisionCache = new Map<string, Revision[]>();
const revisionRequestVersions = new Map<string, number>();
const listeners = new Set<() => void>();
let revisionStoreVersion = 0;

interface RevisionCacheResult {
  readonly revisions: Revision[];
  readonly refreshDocumentRevisions: (documentId: string) => Promise<void>;
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
  useSyncExternalStore(subscribeRevisionStore, getRevisionStoreSnapshot, getRevisionStoreSnapshot);

  const refreshDocumentRevisions = useCallback(
    async (nextDocumentId: string): Promise<void> => {
      const key = cacheKey(projectId, nextDocumentId);
      const requestVersion = (revisionRequestVersions.get(key) ?? 0) + 1;
      revisionRequestVersions.set(key, requestVersion);
      try {
        const response = await api.revisions(projectId, nextDocumentId);
        if (revisionRequestVersions.get(key) !== requestVersion) return;
        replaceCachedRevisions(projectId, nextDocumentId, response.revisions);
      } catch (reason: unknown) {
        if (revisionRequestVersions.get(key) !== requestVersion) return;
        onError(reason);
      }
    },
    [onError, projectId],
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
