import { useCallback, useEffect, useRef, useState } from "react";

import { HttpError } from "@/app/api";

import { toErrorMessage } from "./toErrorMessage";

/**
 * Append one older keyset page after the currently loaded items, skipping
 * entries whose id is already present (pages may overlap across refreshes).
 */
export function appendUniqueById<T>(
  current: readonly T[],
  older: readonly T[],
  idOf: (item: T) => string,
): T[] {
  const known = new Set(current.map(idOf));
  const uniqueOlder = older.filter((item) => {
    const id = idOf(item);
    if (known.has(id)) return false;
    known.add(id);
    return true;
  });
  return [...current, ...uniqueOlder];
}

/**
 * Merge one refreshed cursorless first page into a loaded catalog: prepend
 * and de-duplicate new summaries, preserve a loaded contiguous older tail
 * with its continuation, and replace the cache wholesale when the fresh page
 * exposes an unknown gap instead of splicing across it. `replacedWholesale`
 * reports which branch ran so callers can preempt in-flight older reads.
 */
export function mergeRefreshedKeysetFirstPage<T>(
  currentItems: readonly T[],
  currentCursor: string | null,
  refreshedItems: readonly T[],
  refreshedCursor: string | null,
  idOf: (item: T) => string,
): { items: T[]; nextCursor: string | null; replacedWholesale: boolean } {
  if (currentItems.length === 0 || refreshedCursor === null) {
    return { items: [...refreshedItems], nextCursor: refreshedCursor, replacedWholesale: true };
  }
  const refreshedIds = new Set(refreshedItems.map(idOf));
  const hasOverlap = currentItems.some((item) => refreshedIds.has(idOf(item)));
  if (!hasOverlap) {
    return { items: [...refreshedItems], nextCursor: refreshedCursor, replacedWholesale: true };
  }
  return {
    items: [...refreshedItems, ...currentItems.filter((item) => !refreshedIds.has(idOf(item)))],
    nextCursor: currentCursor,
    replacedWholesale: false,
  };
}

/** One in-flight older-page traversal and its currency markers. */
interface ActiveOlderPageRequest {
  readonly cursor: string;
  readonly controller: AbortController;
  readonly epoch: number;
  promise: Promise<void>;
}

/** The shared older-page traversal every bounded keyset history consumes. */
export interface KeysetOlderPages {
  /** Begin or join the older traversal; blocked or stale calls resolve without requesting. */
  readonly loadOlder: () => Promise<void>;
  readonly isLoadingOlder: boolean;
  readonly olderError: string | null;
  /** Abort the in-flight older read and reset its busy/error state. */
  readonly abortInFlight: () => void;
}

interface UseKeysetOlderPagesOptions<Page> {
  /** Changing this key aborts the in-flight older read and resets its state. */
  readonly cleanupKey: string;
  /** Call-time traversal gate (panel activation, owner validity). */
  readonly isEnabled: () => boolean;
  /** Call-time block while a first-page request owns the surface. */
  readonly isBlocked?: (() => boolean) | undefined;
  /** Exclusive continuation position of the loaded page; null ends the traversal. */
  readonly nextCursor: string | null;
  readonly fetchPage: (cursor: string, signal: AbortSignal) => Promise<Page>;
  /** Publish one currency-validated older page (append-unique, adopt its cursor). */
  readonly commitPage: (page: Page) => void;
  /** Optional outcome channel: null after a committed page, the message after a failure. */
  readonly onOutcome?: ((error: string | null) => void) | undefined;
  /** Optional 401 routing; without it a session loss stays a local older error. */
  readonly onSessionLost?: (() => void) | undefined;
  readonly busyErrorMessage: string;
}

/**
 * One older-page traversal for a bounded keyset history. The traversal owns
 * its single in-flight request, its busy/error state, and two fixed
 * invariants: the busy flag is released only by the request that still owns
 * the traversal epoch (`abortInFlight` resets busy itself when it supersedes
 * one, so a superseded read's `finally` must not clear a successor's busy),
 * and a new request always aborts the controller it replaces before
 * installing its own.
 */
export function useKeysetOlderPages<Page>(
  options: UseKeysetOlderPagesOptions<Page>,
): KeysetOlderPages {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const optionsRef = useRef(options);
  const requestRef = useRef<ActiveOlderPageRequest | null>(null);
  const epochRef = useRef(0);

  useEffect(() => {
    optionsRef.current = options;
  });

  const abortInFlight = useCallback((): void => {
    const inFlight = requestRef.current;
    requestRef.current = null;
    if (inFlight !== null) {
      epochRef.current += 1;
      inFlight.controller.abort();
    }
    setBusy(false);
    setError(null);
  }, []);

  // Owner switches (cleanupKey) must abort any in-flight older-page request:
  // without the abort, a late success would append the previous owner's
  // summaries onto the new owner's empty first page.
  // biome-ignore lint/correctness/useExhaustiveDependencies: cleanupKey is an intentional change trigger for this cleanup-only effect; the abort communicates through refs and state, not through reading it.
  useEffect(() => {
    return () => {
      abortInFlight();
    };
  }, [abortInFlight, options.cleanupKey]);

  const loadOlder = useCallback((): Promise<void> => {
    const current = optionsRef.current;
    const inFlight = requestRef.current;
    if (inFlight !== null && !inFlight.controller.signal.aborted) {
      return inFlight.cursor === current.nextCursor ? inFlight.promise : Promise.resolve();
    }
    if (!current.isEnabled() || current.nextCursor === null || current.isBlocked?.()) {
      return Promise.resolve();
    }
    // Only an already-aborted placeholder can still occupy the slot; abort it
    // anyway so no controller is ever replaced without being aborted.
    inFlight?.controller.abort();
    const controller = new AbortController();
    const request: ActiveOlderPageRequest = {
      cursor: current.nextCursor,
      controller,
      epoch: ++epochRef.current,
      promise: Promise.resolve(),
    };
    const isCurrent = () =>
      requestRef.current === request &&
      epochRef.current === request.epoch &&
      !controller.signal.aborted;

    setBusy(true);
    setError(null);
    request.promise = (async () => {
      try {
        const page = await current.fetchPage(request.cursor, controller.signal);
        if (!isCurrent()) return;
        requestRef.current = null;
        setError(null);
        current.commitPage(page);
        current.onOutcome?.(null);
      } catch (reason) {
        if (!isCurrent()) return;
        requestRef.current = null;
        if (reason instanceof HttpError && reason.status === 401 && current.onSessionLost) {
          current.onSessionLost();
        } else {
          const message = toErrorMessage(reason, current.busyErrorMessage);
          setError(message);
          current.onOutcome?.(message);
        }
      } finally {
        if (requestRef.current === request) requestRef.current = null;
        // Only the request that still owns the traversal epoch may release
        // the busy flag: `abortInFlight` already reset busy when it aborted
        // this read, so a superseded `finally` must not clear a successor's.
        if (epochRef.current === request.epoch) setBusy(false);
      }
    })();
    requestRef.current = request;
    return request.promise;
  }, []);

  return { loadOlder, isLoadingOlder: busy, olderError: error, abortInFlight };
}
