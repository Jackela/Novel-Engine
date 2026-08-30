import { useCallback, useRef, useState } from "react";

export interface PendingActionController<K extends string> {
  /** Reactive snapshot: which action keys are currently in flight. */
  readonly pending: Readonly<Record<K, boolean>>;
  /** Marks `key` in flight; returns false when it is already running. */
  begin: (key: K) => boolean;
  /** Clears the in-flight marker for `key`. */
  finish: (key: K) => void;
}

/**
 * Shared idempotency guard for async UI actions: a ref-backed in-flight set
 * prevents double dispatch during the render gap before state lands, while
 * `pending` mirrors the set for reactive `disabled`/busy rendering.
 */
export function usePendingAction<K extends string>(keys: readonly K[]): PendingActionController<K> {
  const initial = {} as Record<K, boolean>;
  for (const key of keys) initial[key] = false;
  const [pending, setPending] = useState<Record<K, boolean>>(initial);
  const pendingRef = useRef<Set<K> | null>(null);

  const begin = useCallback((key: K) => {
    if (pendingRef.current === null) {
      pendingRef.current = new Set<K>();
    }
    const current = pendingRef.current;
    if (current.has(key)) return false;
    current.add(key);
    setPending((current) => ({ ...current, [key]: true }));
    return true;
  }, []);

  const finish = useCallback((key: K) => {
    pendingRef.current?.delete(key);
    setPending((current) => ({ ...current, [key]: false }));
  }, []);

  return { pending, begin, finish };
}
