import { useCallback, useLayoutEffect, useRef } from "react";

export type InspectorCommand = () => void | Promise<void>;
export type CommandFocusFallback = () => HTMLElement | null;

function canReceiveFocus(element: HTMLElement | null): element is HTMLElement {
  if (element === null || !element.isConnected) return false;
  if (
    (element instanceof HTMLButtonElement ||
      element instanceof HTMLInputElement ||
      element instanceof HTMLSelectElement ||
      element instanceof HTMLTextAreaElement) &&
    element.disabled
  ) {
    return false;
  }
  return true;
}

/**
 * Remembers the exact command trigger and restores focus only when both the
 * command and its controlled pending state have completed.
 */
export function useCommandFocusRestoration(isPending: boolean) {
  const targetRef = useRef<HTMLButtonElement | null>(null);
  const fallbackRef = useRef<CommandFocusFallback | null>(null);
  const settledRef = useRef(false);
  const pendingRef = useRef(isPending);
  const invocationRef = useRef(0);

  const restoreIfReady = useCallback((invocation: number) => {
    if (invocation !== invocationRef.current || !settledRef.current || pendingRef.current) {
      return;
    }
    const target = targetRef.current;
    const activeElement = document.activeElement;
    if (
      activeElement !== null &&
      activeElement !== document.body &&
      activeElement !== document.documentElement &&
      activeElement !== target &&
      activeElement.isConnected
    ) {
      targetRef.current = null;
      fallbackRef.current = null;
      return;
    }
    const focusTarget = canReceiveFocus(target) ? target : fallbackRef.current?.();
    const resolvedFocusTarget = focusTarget ?? null;
    targetRef.current = null;
    fallbackRef.current = null;
    if (canReceiveFocus(resolvedFocusTarget)) resolvedFocusTarget.focus();
  }, []);

  useLayoutEffect(() => {
    pendingRef.current = isPending;
    if (!isPending) {
      restoreIfReady(invocationRef.current);
    }
  }, [isPending, restoreIfReady]);

  return useCallback(
    (
      target: HTMLButtonElement,
      command: InspectorCommand,
      fallback: CommandFocusFallback | null = null,
    ): void | Promise<void> => {
      const invocation = invocationRef.current + 1;
      invocationRef.current = invocation;
      targetRef.current = target;
      fallbackRef.current = fallback;
      settledRef.current = false;

      try {
        const result = command();
        if (result === undefined) {
          settledRef.current = true;
          queueMicrotask(() => restoreIfReady(invocation));
          return;
        }
        return result.finally(() => {
          if (invocation === invocationRef.current) {
            settledRef.current = true;
          }
          restoreIfReady(invocation);
        });
      } catch (error) {
        settledRef.current = true;
        queueMicrotask(() => restoreIfReady(invocation));
        throw error;
      }
    },
    [restoreIfReady],
  );
}
