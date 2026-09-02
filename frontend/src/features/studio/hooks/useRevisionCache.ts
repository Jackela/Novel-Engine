import { useCallback, useEffect, useRef, useSyncExternalStore } from "react";

import { api } from "@/app/api";
import type { RevisionPage, RevisionSummary } from "@/app/types/studio";

const REVISION_PAGE_LIMIT = 50;
const MAX_CACHED_OWNERS = 8;
const emptyRevisions: RevisionSummary[] = [];
const noop = () => undefined;

interface RevisionCacheEntry {
  readonly revisions: RevisionSummary[];
  readonly nextCursor: string | null;
  readonly initialized: boolean;
  readonly lastAccess: number;
}

type RevisionRequestIntent = "activation" | "refresh" | "older";

interface ActiveRevisionRequest {
  readonly key: string;
  readonly intent: RevisionRequestIntent;
  readonly cursor: string | null;
  readonly controller: AbortController;
  readonly version: number;
  promise: Promise<void>;
}

interface RevisionCacheResult {
  readonly revisions: RevisionSummary[];
  readonly historyInitialized: boolean;
  readonly hasOlderRevisions: boolean;
  readonly isLoadingOlder: boolean;
  readonly refreshDocumentRevisions: (documentId: string) => Promise<void>;
  readonly loadOlderRevisions: () => Promise<void>;
}

const revisionCache = new Map<string, RevisionCacheEntry>();
const revisionRequests = new Map<string, ActiveRevisionRequest>();
const activeOwnerCounts = new Map<string, number>();
const listeners = new Set<() => void>();
let revisionStoreVersion = 0;
let accessSequence = 0;
let requestVersion = 0;

function cacheKey(projectId: string, documentId: string): string {
  return `${projectId}\u0000${documentId}`;
}

function emitRevisionStoreChange(): void {
  revisionStoreVersion += 1;
  for (const listener of listeners) listener();
}

function subscribeRevisionStore(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getRevisionStoreSnapshot(): number {
  return revisionStoreVersion;
}

function pruneInactiveOwners(): void {
  while (revisionCache.size > MAX_CACHED_OWNERS) {
    let oldest: [string, RevisionCacheEntry] | undefined;
    for (const candidate of revisionCache) {
      if ((activeOwnerCounts.get(candidate[0]) ?? 0) > 0) continue;
      if (!oldest || candidate[1].lastAccess < oldest[1].lastAccess) oldest = candidate;
    }
    if (!oldest) return;
    revisionCache.delete(oldest[0]);
  }
}

function putEntry(key: string, entry: Omit<RevisionCacheEntry, "lastAccess">): void {
  revisionCache.set(key, { ...entry, lastAccess: ++accessSequence });
  pruneInactiveOwners();
  emitRevisionStoreChange();
}

function ensureEntry(key: string): RevisionCacheEntry {
  const existing = revisionCache.get(key);
  if (existing) return existing;
  const entry: RevisionCacheEntry = {
    revisions: emptyRevisions,
    nextCursor: null,
    initialized: false,
    lastAccess: ++accessSequence,
  };
  revisionCache.set(key, entry);
  pruneInactiveOwners();
  return entry;
}

function appendUnique(
  current: readonly RevisionSummary[],
  additions: readonly RevisionSummary[],
): RevisionSummary[] {
  const known = new Set(current.map((revision) => revision.id));
  return [
    ...current,
    ...additions.filter((revision) => {
      if (known.has(revision.id)) return false;
      known.add(revision.id);
      return true;
    }),
  ];
}

function mergeFreshPage(
  current: RevisionCacheEntry,
  page: RevisionPage,
): Pick<RevisionCacheEntry, "revisions" | "nextCursor"> {
  if (!current.initialized || page.next_cursor === null) {
    return { revisions: page.revisions, nextCursor: page.next_cursor };
  }
  const currentIds = new Set(current.revisions.map((revision) => revision.id));
  const overlaps = page.revisions.some((revision) => currentIds.has(revision.id));
  if (!overlaps) {
    // The cache is more than one page behind. Appending would fabricate a
    // contiguous History range across revisions the client has not loaded.
    return { revisions: page.revisions, nextCursor: page.next_cursor };
  }
  return {
    revisions: appendUnique(page.revisions, current.revisions),
    nextCursor: current.nextCursor,
  };
}

function abortOwnerRequest(key: string): void {
  const active = revisionRequests.get(key);
  if (!active) return;
  revisionRequests.delete(key);
  active.controller.abort();
  emitRevisionStoreChange();
}

function activateOwner(key: string): () => void {
  activeOwnerCounts.set(key, (activeOwnerCounts.get(key) ?? 0) + 1);
  const entry = ensureEntry(key);
  revisionCache.set(key, { ...entry, lastAccess: ++accessSequence });
  return () => {
    const remaining = (activeOwnerCounts.get(key) ?? 1) - 1;
    if (remaining > 0) {
      activeOwnerCounts.set(key, remaining);
    } else {
      activeOwnerCounts.delete(key);
      abortOwnerRequest(key);
      pruneInactiveOwners();
    }
  };
}

function beginRequest(
  projectId: string,
  documentId: string,
  intent: RevisionRequestIntent,
  cursor: string | null,
  onError: (reason: unknown) => void,
  onSuccess: () => void,
): Promise<void> {
  const key = cacheKey(projectId, documentId);
  const existing = revisionRequests.get(key);
  if (existing && !existing.controller.signal.aborted) {
    if (existing.intent === intent && existing.cursor === cursor) return existing.promise;
    if (intent === "older") return Promise.resolve();
    abortOwnerRequest(key);
  }

  const currentAtStart = ensureEntry(key);
  revisionCache.set(key, { ...currentAtStart, lastAccess: ++accessSequence });
  pruneInactiveOwners();
  const controller = new AbortController();
  const version = ++requestVersion;
  const request: ActiveRevisionRequest = {
    key,
    intent,
    cursor,
    controller,
    version,
    promise: Promise.resolve(),
  };
  const isCurrent = () =>
    !controller.signal.aborted &&
    revisionRequests.get(key) === request &&
    revisionRequests.get(key)?.version === version &&
    (activeOwnerCounts.get(key) ?? 0) > 0;

  request.promise = (async () => {
    try {
      const page = await api.revisions(projectId, documentId, {
        limit: REVISION_PAGE_LIMIT,
        ...(cursor === null ? {} : { cursor }),
        signal: controller.signal,
      });
      if (!isCurrent()) return;
      const current = revisionCache.get(key) ?? currentAtStart;
      if (intent === "older") {
        if (page.next_cursor === cursor) {
          onError(new Error("The revision service repeated its continuation cursor."));
          return;
        }
        putEntry(key, {
          revisions: appendUnique(current.revisions, page.revisions),
          nextCursor: page.next_cursor,
          initialized: true,
        });
      } else {
        putEntry(key, {
          ...mergeFreshPage(current, page),
          initialized: true,
        });
      }
      onSuccess();
    } catch (reason) {
      if (isCurrent()) onError(reason);
    } finally {
      if (revisionRequests.get(key) === request) {
        revisionRequests.delete(key);
        emitRevisionStoreChange();
      }
    }
  })();
  revisionRequests.set(key, request);
  emitRevisionStoreChange();
  return request.promise;
}

export function useRevisionCache(
  projectId: string,
  documentId: string | null,
  onError: (reason: unknown) => void,
  onSuccess: () => void = noop,
): RevisionCacheResult {
  useSyncExternalStore(subscribeRevisionStore, getRevisionStoreSnapshot, getRevisionStoreSnapshot);
  const key = documentId ? cacheKey(projectId, documentId) : null;
  const ownerKeyRef = useRef<string | null>(null);

  useEffect(() => {
    if (key === null) return;
    ownerKeyRef.current = key;
    const deactivate = activateOwner(key);
    return () => {
      if (ownerKeyRef.current === key) ownerKeyRef.current = null;
      deactivate();
    };
  }, [key]);

  const refreshDocumentRevisions = useCallback(
    (nextDocumentId: string): Promise<void> => {
      const nextKey = cacheKey(projectId, nextDocumentId);
      if (ownerKeyRef.current !== nextKey) return Promise.resolve();
      return beginRequest(projectId, nextDocumentId, "refresh", null, onError, onSuccess);
    },
    [onError, onSuccess, projectId],
  );

  useEffect(() => {
    if (documentId === null || key === null) return;
    void beginRequest(projectId, documentId, "activation", null, onError, onSuccess);
  }, [documentId, key, onError, onSuccess, projectId]);

  const entry = key ? revisionCache.get(key) : undefined;
  const loadOlderRevisions = useCallback((): Promise<void> => {
    if (documentId === null || key === null || ownerKeyRef.current !== key) {
      return Promise.resolve();
    }
    const current = revisionCache.get(key);
    if (!current?.initialized || current.nextCursor === null) return Promise.resolve();
    return beginRequest(projectId, documentId, "older", current.nextCursor, onError, onSuccess);
  }, [documentId, key, onError, onSuccess, projectId]);
  const activeRequest = key ? revisionRequests.get(key) : undefined;

  return {
    revisions: entry?.revisions ?? emptyRevisions,
    historyInitialized: entry?.initialized ?? false,
    hasOlderRevisions: entry?.initialized === true && entry.nextCursor !== null,
    isLoadingOlder: activeRequest?.intent === "older" && !activeRequest.controller.signal.aborted,
    refreshDocumentRevisions,
    loadOlderRevisions,
  };
}

/** Test isolation for this module-level bounded cache. */
export function resetRevisionCacheForTests(): void {
  for (const request of revisionRequests.values()) request.controller.abort();
  revisionRequests.clear();
  revisionCache.clear();
  activeOwnerCounts.clear();
  emitRevisionStoreChange();
}

export function revisionCacheStatsForTests(): {
  readonly cachedOwners: number;
  readonly requestingOwners: number;
} {
  return { cachedOwners: revisionCache.size, requestingOwners: revisionRequests.size };
}
