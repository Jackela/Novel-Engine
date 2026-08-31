import { Sparkles } from "lucide-react";
import { useCallback, useLayoutEffect, useRef } from "react";

import type { WholeBookPhase } from "../hooks/useWholeBookLoop";

type WholeBookCommand = () => void | Promise<void>;

interface StudioWholeBookControlProps {
  /** Loop state machine snapshot (#318). */
  phase: WholeBookPhase;
  /** Chapters still needing generation at render time (plan size). */
  remaining: number;
  onStart: WholeBookCommand;
  onStop: WholeBookCommand;
}

function chaptersLabel(count: number): string {
  return count === 1 ? "1 chapter" : `${count} chapters`;
}

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
function useWholeBookFocusReturn(isBusy: boolean, canStart: boolean) {
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

/**
 * Manuscript-surface control for the whole-book generation loop (#318).
 * Shows progress ("chapter k / n") plus a visible stop control while the
 * loop runs, and reports what a stop or failure preserved afterwards.
 */
export function StudioWholeBookControl({
  phase,
  remaining,
  onStart,
  onStop,
}: StudioWholeBookControlProps) {
  const isBusy = phase.kind === "running";
  const canStart = remaining > 0;
  const { outcomeFallbackRef, startButtonRef, runCommand } = useWholeBookFocusReturn(
    isBusy,
    canStart,
  );

  return (
    <section
      aria-label="Whole book generation"
      className="whole-book"
      ref={outcomeFallbackRef}
      tabIndex={-1}
    >
      <p className="whole-book__hint">
        Drafts and auto-accepts every chapter still missing an AI revision, in reading order.
      </p>
      {isBusy ? (
        <>
          <p className="whole-book__status" role="status">
            Generating chapter {phase.current} of {phase.total}…
          </p>
          <button
            className="ui-command whole-book__stop"
            onClick={() => runCommand(onStop)}
            type="button"
          >
            Stop generating
          </button>
        </>
      ) : (
        <>
          <button
            className="ui-command"
            disabled={!canStart}
            onClick={() => runCommand(onStart)}
            ref={startButtonRef}
            title={
              remaining === 0 ? "Every chapter already has an accepted AI revision" : undefined
            }
            type="button"
          >
            <Sparkles aria-hidden="true" /> Generate whole book
          </button>
          {phase.kind === "done" ? (
            <p className="whole-book__outcome" role="status">
              {phase.stoppedEarly
                ? `Stopped — ${chaptersLabel(phase.generated)} accepted this run.`
                : phase.generated === 0
                  ? "Every chapter already has an accepted AI revision."
                  : `Completed — ${chaptersLabel(phase.generated)} accepted.`}
            </p>
          ) : null}
          {phase.kind === "failed" ? (
            <p className="ui-form-error whole-book__failure" role="alert">
              Failed on “{phase.failedChapterTitle}” after {chaptersLabel(phase.generated)}{" "}
              accepted: {phase.message}
            </p>
          ) : null}
        </>
      )}
    </section>
  );
}
