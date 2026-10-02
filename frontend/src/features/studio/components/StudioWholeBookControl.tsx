import { Sparkles } from "lucide-react";
import { useCallback, useLayoutEffect, useRef, useState } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";
import type { ProposalAuditStatus } from "../hooks/useStudioJobs";
import type { WholeBookChapter, WholeBookPhase } from "../hooks/useWholeBookLoop";
import { ProposalOutcomeAuditNotice } from "./ProposalOutcomeAuditNotice";

type WholeBookCommand = () => void | Promise<void>;

interface StudioWholeBookControlProps {
  /** Loop state machine snapshot (#318). */
  phase: WholeBookPhase;
  /** Chapters a run could still touch (safe plus confirmation-gated). */
  remaining: number;
  /** Dry-run list: chapters a confirmed run would replace (#DR-007). */
  occupiedChapters?: readonly WholeBookChapter[];
  /** How many of `remaining` are empty and may start without confirmation. */
  safeCount?: number;
  onStart: WholeBookCommand;
  /** Replacing occupied chapters; absent, the control never offers it. */
  onConfirmReplace?: WholeBookCommand;
  onStop: WholeBookCommand;
  proposalOutcomeUnknown?: boolean;
  proposalAuditStatus?: ProposalAuditStatus;
  onRetryProposalAudit?: WholeBookCommand;
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

/** Whole-book progress, stop, preserved-work, and unknown-outcome controls (#318). */
export function StudioWholeBookControl({
  phase,
  remaining,
  occupiedChapters = [],
  safeCount = Math.max(remaining - occupiedChapters.length, 0),
  onStart,
  onConfirmReplace,
  onStop,
  proposalOutcomeUnknown = false,
  proposalAuditStatus = "idle",
  onRetryProposalAudit,
}: StudioWholeBookControlProps) {
  const { t } = useTranslation();
  const [isConfirming, setIsConfirming] = useState(false);
  const emptyActionRef = useRef<HTMLButtonElement | null>(null);
  const replaceActionRef = useRef<HTMLButtonElement | null>(null);
  const restoreStartFocusRef = useRef(false);
  const isBusy = phase.kind === "running";
  const canStart = remaining > 0;
  const { outcomeFallbackRef, startButtonRef, runCommand } = useWholeBookFocusReturn(
    isBusy,
    canStart,
  );
  // The replacement choice exists only while the model supplies both the
  // affected chapters and its command; a start with no such command runs the
  // empty chapters alone instead of silently overwriting text (#DR-007).
  const canConfirmReplace = occupiedChapters.length > 0 && onConfirmReplace !== undefined;
  const showConfirmation = isConfirming && canConfirmReplace && !isBusy && !proposalOutcomeUnknown;
  /** The plural-aware count unit ("chapter"/"chapters") for outcome sentences. */
  const chaptersUnit = (count: number) => (count === 1 ? t("noun.chapter") : t("noun.chapters"));

  // Opening the surface hands focus to its first action so keyboard authors
  // read the dry-run list before firing; cancelling returns focus to the Start
  // command that opened it, mirroring the navigator's delete confirmation.
  useLayoutEffect(() => {
    if (showConfirmation) {
      (safeCount > 0 ? emptyActionRef.current : replaceActionRef.current)?.focus();
      return;
    }
    if (restoreStartFocusRef.current && startButtonRef.current !== null) {
      restoreStartFocusRef.current = false;
      startButtonRef.current.focus();
    }
  }, [safeCount, showConfirmation, startButtonRef]);

  const cancelConfirmation = () => {
    restoreStartFocusRef.current = true;
    setIsConfirming(false);
  };
  const runConfirmation = (command: WholeBookCommand) => {
    setIsConfirming(false);
    runCommand(command);
  };

  return (
    <section
      aria-label={t("wholeBook.region")}
      className="whole-book"
      onKeyDown={(event) => {
        if (event.key === "Escape" && showConfirmation) {
          event.stopPropagation();
          cancelConfirmation();
        }
      }}
      ref={outcomeFallbackRef}
      tabIndex={-1}
    >
      <p className="whole-book__hint">{t("wholeBook.hint")}</p>
      {proposalOutcomeUnknown ? (
        <ProposalOutcomeAuditNotice
          onGenerateAnother={() => runCommand(onStart)}
          onRetry={onRetryProposalAudit ? () => runCommand(onRetryProposalAudit) : undefined}
          status={proposalAuditStatus}
        />
      ) : isBusy ? (
        <>
          <p className="whole-book__status" role="status">
            {t("wholeBook.status.generating", { current: phase.current, total: phase.total })}
          </p>
          <button
            className="ui-command whole-book__stop"
            onClick={() => runCommand(onStop)}
            type="button"
          >
            {t("wholeBook.action.stop")}
          </button>
        </>
      ) : showConfirmation ? (
        <>
          <p className="whole-book__hint">{t("wholeBook.confirm.message")}</p>
          <ul aria-label={t("wholeBook.confirm.listLabel")} className="whole-book__hint">
            {occupiedChapters.map((chapter) => (
              <li key={chapter.id}>{chapter.title}</li>
            ))}
          </ul>
          {safeCount > 0 ? (
            <button
              className="ui-command"
              onClick={() => runConfirmation(onStart)}
              ref={emptyActionRef}
              type="button"
            >
              {t("wholeBook.action.generateEmpty", {
                count: safeCount,
                unit: chaptersUnit(safeCount),
              })}
            </button>
          ) : null}
          <button
            className="ui-command"
            onClick={() => runConfirmation(onConfirmReplace ?? onStart)}
            ref={replaceActionRef}
            type="button"
          >
            {t("wholeBook.action.replaceOccupied", {
              count: occupiedChapters.length,
              unit: chaptersUnit(occupiedChapters.length),
            })}
          </button>
          <button className="ui-command" onClick={cancelConfirmation} type="button">
            {t("wholeBook.action.cancel")}
          </button>
        </>
      ) : (
        <>
          <button
            className="ui-command"
            disabled={!canStart}
            onClick={() => {
              if (canConfirmReplace) {
                setIsConfirming(true);
                return;
              }
              runCommand(onStart);
            }}
            ref={startButtonRef}
            title={remaining === 0 ? t("wholeBook.title.done") : undefined}
            type="button"
          >
            <Sparkles aria-hidden="true" /> {t("wholeBook.action.start")}
          </button>
          {phase.kind === "done" ? (
            <p className="whole-book__outcome" role="status">
              {phase.stoppedEarly
                ? t("wholeBook.outcome.stoppedEarly", {
                    count: phase.generated,
                    unit: chaptersUnit(phase.generated),
                  })
                : phase.generated === 0
                  ? t("wholeBook.outcome.alreadyDone")
                  : t("wholeBook.outcome.completed", {
                      count: phase.generated,
                      unit: chaptersUnit(phase.generated),
                    })}
            </p>
          ) : null}
          {phase.kind === "failed" ? (
            <p className="ui-form-error whole-book__failure" role="alert">
              {t("wholeBook.failure", {
                title: phase.failedChapterTitle,
                count: phase.generated,
                unit: chaptersUnit(phase.generated),
                message: phase.message,
              })}
            </p>
          ) : null}
        </>
      )}
    </section>
  );
}
