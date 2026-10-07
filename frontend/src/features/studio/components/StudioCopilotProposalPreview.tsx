import { Check, X } from "lucide-react";

import { useTranslation } from "@/app/i18n/useTranslation";
import type { StudioJob } from "@/app/types/studio";

interface StudioCopilotProposalPreviewProps {
  /** True while accepting the displayed proposal. */
  readonly accepting: boolean;
  /** True while any proposal command or audit owns the panel. */
  readonly busy: boolean;
  readonly onAccept: (target: HTMLButtonElement) => void;
  readonly onReject: () => void;
  readonly proposal: StudioJob;
}

/**
 * A settled proposal awaiting the author's verdict: read-only
 * markdown preview where Accept is the only path that applies
 * the proposal to the manuscript.
 */
export function StudioCopilotProposalPreview({
  accepting,
  busy,
  onAccept,
  onReject,
  proposal,
}: StudioCopilotProposalPreviewProps) {
  const { t } = useTranslation();
  return (
    <section className="studio-inspector__proposal">
      <header>
        <strong>{t("copilot.proposal.heading")}</strong>
        <span>{t("copilot.proposal.previewOnly")}</span>
      </header>
      <pre>{proposal.result.proposal_markdown}</pre>
      <div className="studio-inspector__actions">
        <button
          aria-busy={accepting}
          className="ui-command ui-command--primary"
          disabled={busy}
          onClick={(event) => {
            onAccept(event.currentTarget);
          }}
          type="button"
        >
          <Check /> {t("copilot.action.accept")}
        </button>
        <button className="ui-command" disabled={busy} onClick={onReject} type="button">
          <X /> {t("copilot.action.reject")}
        </button>
      </div>
    </section>
  );
}
