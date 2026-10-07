import { useCallback, useLayoutEffect, useRef } from "react";

export type WholeBookCommand = () => void | Promise<void>;

interface PendingFocusReturn {
  readonly invocation: number;
  settled: boolean;
}

/**
 * Start and Stop replace one another, so the exact trigger cannot survive the
 * command. Restore to the semantically equivalent Start control only when the
 * removed trigger left focus orphaned on the document body. A user's deliberate
 * focus move always wins.
 */
export function useWholeBookFocusReturn(isBusy: boolean, canStart: boolean) {
  const startButtonRef = useRef<HTMLButtonElement | null>(null);
  const outcomeFallbackRef = useRef<HTMLElement | null>(null);
  const pendingRef = useRef<PendingFocusReturn | null>(null);
  const invocationRef = useRef(0);
  const isBusyRef = useRef(isBusy);
  const canStartRef = useRef(canStart);

  const restoreIfReady = useCallback(
    (invocation: number, busy = isBusyRef.current, startAvailable = canStartRef.current) => {
      const pending = pendingRef.current;
      if (pending === null || pending.invocation !== invocation || !pending.settled || busy) {
        return;
      }

      const active = document.activeElement;
      const startTarget = startButtonRef.current;
      if (active === startTarget) {
        pendingRef.current = null;
        return;
      }
      if (active !== null && active !== document.body && active.isConnected) {
        pendingRef.current = null;
        return;
      }

      const target =
        startAvailable && startTarget?.isConnected && !startTarget.disabled
          ? startTarget
          : outcomeFallbackRef.current;
      if (target === null || !target.isConnected) {
        pendingRef.current = null;
        return;
      }

      target.focus();
      pendingRef.current = null;
    },
    [],
  );

  useLayoutEffect(() => {
    isBusyRef.current = isBusy;
    canStartRef.current = canStart;
    const pending = pendingRef.current;
    if (pending !== null) restoreIfReady(pending.invocation, isBusy, canStart);
  }, [canStart, isBusy, restoreIfReady]);

  const runCommand = useCallback(
    (command: WholeBookCommand) => {
      const invocation = invocationRef.current + 1;
      invocationRef.current = invocation;
      const pending: PendingFocusReturn = { invocation, settled: false };
      pendingRef.current = pending;

      const settle = () => {
        if (pendingRef.current?.invocation !== invocation) return;
        pending.settled = true;
        restoreIfReady(invocation);
      };

      try {
        const result = command();
        if (result === undefined) {
          pending.settled = true;
          queueMicrotask(() => restoreIfReady(invocation));
          return;
        }
        void result.then(settle, settle);
      } catch (error) {
        pending.settled = true;
        queueMicrotask(() => restoreIfReady(invocation));
        throw error;
      }
    },
    [restoreIfReady],
  );

  return { outcomeFallbackRef, startButtonRef, runCommand };
}
