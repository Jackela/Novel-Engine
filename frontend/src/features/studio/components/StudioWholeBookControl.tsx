import { Sparkles } from "lucide-react";

import type { WholeBookPhase } from "../hooks/useWholeBookLoop";

interface StudioWholeBookControlProps {
  /** Loop state machine snapshot (#318). */
  phase: WholeBookPhase;
  /** Chapters still needing generation at render time (plan size). */
  remaining: number;
  onStart: () => void;
  onStop: () => void;
}

function chaptersLabel(count: number): string {
  return count === 1 ? "1 chapter" : `${count} chapters`;
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

  return (
    <section aria-label="Whole book generation" className="whole-book">
      <p className="whole-book__hint">
        Drafts and auto-accepts every chapter still missing an AI revision, in reading order.
      </p>
      {isBusy ? (
        <>
          <p className="whole-book__status" role="status">
            Generating chapter {phase.current} of {phase.total}…
          </p>
          <button className="ui-command whole-book__stop" onClick={onStop} type="button">
            Stop generating
          </button>
        </>
      ) : (
        <>
          <button
            className="ui-command"
            disabled={remaining === 0}
            onClick={onStart}
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
