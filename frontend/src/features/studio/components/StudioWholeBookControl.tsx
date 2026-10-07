import { Sparkles } from "lucide-react";
import { useLayoutEffect, useRef, useState } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";
import type { ProposalAuditStatus } from "../hooks/useStudioJobs";
import { useWholeBookFocusReturn, type WholeBookCommand } from "../hooks/useWholeBookFocusReturn";
import type { WholeBookChapter, WholeBookPhase } from "../hooks/useWholeBookLoop";
import { ProposalOutcomeAuditNotice } from "./ProposalOutcomeAuditNotice";
import { StudioWholeBookReplaceConfirm } from "./StudioWholeBookReplaceConfirm";

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
        <StudioWholeBookReplaceConfirm
          cancelConfirmation={cancelConfirmation}
          chaptersUnit={chaptersUnit}
          emptyActionRef={emptyActionRef}
          occupiedChapters={occupiedChapters}
          onConfirmReplace={onConfirmReplace}
          onStart={onStart}
          replaceActionRef={replaceActionRef}
          runConfirmation={runConfirmation}
          safeCount={safeCount}
        />
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
