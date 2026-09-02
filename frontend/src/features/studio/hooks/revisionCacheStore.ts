import { api } from "@/app/api";
import type { RevisionSummary } from "@/app/types/studio";

import { appendUnique, mergeFreshPage, type RevisionCacheEntry } from "./revisionCachePages";
import type {
  ActiveRevisionRequest,
  QueuedOlderRequest,
  RevisionOwnerState,
  RevisionRequestIntent,
  RevisionSubscriber,
} from "./revisionCacheTypes";

export type { RevisionSubscriber } from "./revisionCacheTypes";

const PAGE_LIMIT = 50;
const OWNER_BUDGET = 8;
const emptyRevisions: RevisionSummary[] = [];

const cache = new Map<string, RevisionCacheEntry>();
const requests = new Map<string, ActiveRevisionRequest>();
const olderQueue = new Map<string, QueuedOlderRequest>();
const activeOwners = new Map<string, number>();
const subscribers = new Map<string, Map<symbol, RevisionSubscriber>>();
const listeners = new Set<() => void>();
let storeVersion = 0;
let accessSequence = 0;
let requestVersion = 0;

export function revisionCacheKey(projectId: string, documentId: string): string {
  return `${projectId}\u0000${documentId}`;
}

function emit(): void {
  storeVersion += 1;
  for (const listener of listeners) listener();
}

export function subscribeRevisionCache(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getRevisionCacheVersion(): number {
  return storeVersion;
}

function prune(): void {
  const budget = Math.max(OWNER_BUDGET, activeOwners.size);
  while (cache.size > budget) {
    let oldest: [string, RevisionCacheEntry] | undefined;
    for (const candidate of cache) {
      if (activeOwners.has(candidate[0])) continue;
      if (!oldest || candidate[1].lastAccess < oldest[1].lastAccess) oldest = candidate;
    }
    if (!oldest) return;
    cache.delete(oldest[0]);
    abortRequest(oldest[0]);
    finishOlderQueue(oldest[0]);
    subscribers.delete(oldest[0]);
  }
}

function put(key: string, entry: Omit<RevisionCacheEntry, "lastAccess">): void {
  cache.set(key, { ...entry, lastAccess: ++accessSequence });
  prune();
  emit();
}

function ensure(key: string): RevisionCacheEntry {
  const existing = cache.get(key);
  if (existing) return existing;
  const entry = { revisions: emptyRevisions, nextCursor: null, initialized: false, lastAccess: 0 };
  cache.set(key, { ...entry, lastAccess: ++accessSequence });
  prune();
  return entry;
}

function abortRequest(key: string): void {
  const request = requests.get(key);
  if (!request) return;
  requests.delete(key);
  request.controller.abort();
  emit();
}

function finishOlderQueue(key: string): void {
  const queued = olderQueue.get(key);
  if (!queued) return;
  olderQueue.delete(key);
  queued.resolve();
  emit();
}

function queueOlder(key: string, projectId: string, documentId: string): QueuedOlderRequest {
  const existing = olderQueue.get(key);
  if (existing) return existing;
  let resolve!: () => void;
  const promise = new Promise<void>((done) => {
    resolve = done;
  });
  const queued = { projectId, documentId, promise, resolve };
  olderQueue.set(key, queued);
  emit();
  return queued;
}

export function activateRevisionOwner(
  key: string,
  token: symbol,
  subscriber: RevisionSubscriber,
): () => void {
  activeOwners.set(key, (activeOwners.get(key) ?? 0) + 1);
  const ownerSubscribers = subscribers.get(key) ?? new Map<symbol, RevisionSubscriber>();
  ownerSubscribers.set(token, subscriber);
  subscribers.set(key, ownerSubscribers);
  const entry = ensure(key);
  cache.set(key, { ...entry, lastAccess: ++accessSequence });
  return () => {
    const current = subscribers.get(key);
    current?.delete(token);
    if (current?.size === 0) subscribers.delete(key);
    const remaining = (activeOwners.get(key) ?? 1) - 1;
    if (remaining > 0) {
      activeOwners.set(key, remaining);
      return;
    }
    activeOwners.delete(key);
    abortRequest(key);
    finishOlderQueue(key);
    prune();
  };
}

function notifySuccess(key: string): void {
  const snapshot = [...(subscribers.get(key)?.values() ?? [])];
  for (const subscriber of snapshot) subscriber.onSuccess();
}

function notifyError(key: string, reason: unknown): void {
  const snapshot = [...(subscribers.get(key)?.values() ?? [])];
  for (const subscriber of snapshot) subscriber.onError(reason);
}

function drainOlder(key: string): void {
  const queued = olderQueue.get(key);
  if (!queued || requests.has(key)) return;
  const entry = cache.get(key);
  if (!entry?.initialized || entry.nextCursor === null || !activeOwners.has(key)) {
    finishOlderQueue(key);
    return;
  }
  void beginRequest(queued.projectId, queued.documentId, "older", entry.nextCursor, null, queued);
}

function beginRequest(
  projectId: string,
  documentId: string,
  intent: RevisionRequestIntent,
  cursor: string | null,
  expectedRevisionId: string | null,
  olderWaiter: QueuedOlderRequest | null = null,
): Promise<void> {
  const key = revisionCacheKey(projectId, documentId);
  const existing = requests.get(key);
  if (existing && !existing.controller.signal.aborted) {
    const same =
      existing.intent === intent &&
      existing.cursor === cursor &&
      existing.expectedRevisionId === expectedRevisionId;
    if (same) return existing.promise;
    if (intent === "older") return queueOlder(key, projectId, documentId).promise;
    if (existing.intent === "older") queueOlder(key, projectId, documentId);
    abortRequest(key);
  }

  const currentAtStart = ensure(key);
  cache.set(key, { ...currentAtStart, lastAccess: ++accessSequence });
  prune();
  const controller = new AbortController();
  const version = ++requestVersion;
  const request: ActiveRevisionRequest = {
    intent,
    cursor,
    expectedRevisionId,
    controller,
    version,
    olderWaiter,
    promise: Promise.resolve(),
  };
  const isCurrent = () =>
    !controller.signal.aborted &&
    requests.get(key) === request &&
    request.version === version &&
    activeOwners.has(key);

  request.promise = (async () => {
    let outcome: { kind: "success" } | { kind: "error"; reason: unknown } | null = null;
    try {
      const page = await api.revisions(projectId, documentId, {
        limit: PAGE_LIMIT,
        ...(cursor === null ? {} : { cursor }),
        signal: controller.signal,
      });
      if (!isCurrent()) return;
      const current = cache.get(key) ?? currentAtStart;
      if (intent === "older") {
        if (page.next_cursor === cursor) {
          outcome = {
            kind: "error",
            reason: new Error("The revision service repeated its continuation cursor."),
          };
          return;
        }
        put(key, {
          revisions: appendUnique(current.revisions, page.revisions),
          nextCursor: page.next_cursor,
          initialized: true,
        });
      } else {
        put(key, { ...mergeFreshPage(current, page), initialized: true });
      }
      outcome = { kind: "success" };
    } catch (error) {
      if (isCurrent()) outcome = { kind: "error", reason: error };
    } finally {
      if (requests.get(key) === request) {
        requests.delete(key);
        emit();
        if (outcome?.kind === "success") notifySuccess(key);
        else if (outcome?.kind === "error") notifyError(key, outcome.reason);
        if (intent === "older" && olderWaiter !== null && olderQueue.get(key) === olderWaiter) {
          finishOlderQueue(key);
        } else {
          drainOlder(key);
        }
      }
    }
  })();
  requests.set(key, request);
  emit();
  return request.promise;
}

export function requestInitialRevisions(projectId: string, documentId: string): Promise<void> {
  const key = revisionCacheKey(projectId, documentId);
  const active = requests.get(key);
  if (active && !active.controller.signal.aborted) return active.promise;
  if ((activeOwners.get(key) ?? 0) > 1 && cache.get(key)?.initialized) {
    return Promise.resolve();
  }
  return beginRequest(projectId, documentId, "activation", null, null);
}

export function requestRevisionRefresh(
  projectId: string,
  documentId: string,
  expectedRevisionId: string,
): Promise<void> {
  return beginRequest(projectId, documentId, "refresh", null, expectedRevisionId);
}

export function requestOlderRevisions(projectId: string, documentId: string): Promise<void> {
  const key = revisionCacheKey(projectId, documentId);
  const entry = cache.get(key);
  if (!entry?.initialized || entry.nextCursor === null) return Promise.resolve();
  const queued = queueOlder(key, projectId, documentId);
  drainOlder(key);
  return queued.promise;
}

export function getRevisionOwnerState(key: string | null): RevisionOwnerState {
  const entry = key ? cache.get(key) : undefined;
  const request = key ? requests.get(key) : undefined;
  const queued = key ? olderQueue.has(key) : false;
  return {
    revisions: entry?.revisions ?? emptyRevisions,
    initialized: entry?.initialized ?? false,
    hasOlder: entry?.initialized === true && entry.nextCursor !== null,
    isLoadingOlder: queued || (request?.intent === "older" && !request.controller.signal.aborted),
    isLoading: queued || (request !== undefined && !request.controller.signal.aborted),
  };
}

export function resetRevisionCacheStore(): void {
  for (const request of requests.values()) request.controller.abort();
  requests.clear();
  for (const queued of olderQueue.values()) queued.resolve();
  olderQueue.clear();
  cache.clear();
  activeOwners.clear();
  subscribers.clear();
  emit();
}

export function getRevisionCacheStats(): { cachedOwners: number; requestingOwners: number } {
  return { cachedOwners: cache.size, requestingOwners: requests.size };
}
