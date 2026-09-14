import { Sparkles } from "lucide-react";
import { useCallback, useLayoutEffect, useRef } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";
import type { ProposalAuditStatus } from "../hooks/useStudioJobs";
import type { WholeBookPhase } from "../hooks/useWholeBookLoop";
import { ProposalOutcomeAuditNotice } from "./ProposalOutcomeAuditNotice";

type WholeBookCommand = () => void | Promise<void>;

interface StudioWholeBookControlProps {
  /** Loop state machine snapshot (#318). */
  phase: WholeBookPhase;
  /** Chapters still needing generation at render time (plan size). */
  remaining: number;
  onStart: WholeBookCommand;
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
  onStart,
  onStop,
  proposalOutcomeUnknown = false,
  proposalAuditStatus = "idle",
  onRetryProposalAudit,
}: StudioWholeBookControlProps) {
  const { t } = useTranslation();
  const isBusy = phase.kind === "running";
  const canStart = remaining > 0;
  const { outcomeFallbackRef, startButtonRef, runCommand } = useWholeBookFocusReturn(
    isBusy,
    canStart,
  );
  /** The plural-aware count unit ("chapter"/"chapters") for outcome sentences. */
  const chaptersUnit = (count: number) => (count === 1 ? t("noun.chapter") : t("noun.chapters"));

  return (
    <section
      aria-label={t("wholeBook.region")}
      className="whole-book"
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
      ) : (
        <>
          <button
            className="ui-command"
            disabled={!canStart}
            onClick={() => runCommand(onStart)}
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
