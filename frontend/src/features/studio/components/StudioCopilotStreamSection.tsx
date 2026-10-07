import { Copy, X } from "lucide-react";

import { useTranslation } from "@/app/i18n/useTranslation";

interface StudioCopilotStreamSectionProps {
  /** DR-006: the stream failed mid-flight; the text is the preserved partial. */
  readonly interrupted: boolean;
  /** DR-010: the author stopped the stream; the text is the kept partial. */
  readonly stopped: boolean;
  /** The markdown received so far while the stream runs (#308). */
  readonly streamingText: string;
  readonly onCopy: () => void;
  readonly onStop: (target: HTMLButtonElement) => void;
}

/**
 * The proposal stream in flight or preserved: live text under an
 * aria-live region with a Stop command, or — once DR-006/DR-010
 * settled it — the same text with a Copy command instead, so a
 * settled stream stays readable and reusable.
 */
export function StudioCopilotStreamSection({
  interrupted,
  onCopy,
  onStop,
  stopped,
  streamingText,
}: StudioCopilotStreamSectionProps) {
  const { t } = useTranslation();
  /** DR-006/DR-010: a settled stream keeps its received text readable. */
  const streamTextKept = interrupted || stopped;
  return (
    <section aria-busy={streamTextKept ? undefined : true} className="studio-inspector__proposal">
      <header>
        <strong>{t("copilot.proposal.heading")}</strong>
        <span>
          {interrupted
            ? t("copilot.proposal.interrupted")
            : stopped
              ? t("copilot.proposal.stopped")
              : t("copilot.proposal.streaming")}
        </span>
      </header>
      <pre aria-live="polite">{streamingText}</pre>
      <div className="studio-inspector__actions">
        {streamTextKept ? (
          <button className="ui-command" onClick={onCopy} type="button">
            <Copy /> {t("copilot.action.copy")}
          </button>
        ) : (
          <button
            className="ui-command"
            onClick={(event) => onStop(event.currentTarget)}
            type="button"
          >
            <X /> {t("copilot.action.stop")}
          </button>
        )}
      </div>
    </section>
  );
}
