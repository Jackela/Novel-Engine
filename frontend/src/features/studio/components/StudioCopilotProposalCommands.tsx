import { Sparkles } from "lucide-react";
import type { RefObject } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";

interface StudioCopilotProposalCommandsProps {
  /** True while any proposal command or audit owns the panel. */
  readonly busy: boolean;
  /** The operation whose command is in flight, when any. */
  readonly pendingOperation: "continue" | "rewrite" | null;
  /** The Continue command element; sibling focus fallbacks anchor here. */
  readonly continueButtonRef: RefObject<HTMLButtonElement | null>;
  readonly onRunCommand: (operation: "continue" | "rewrite", target: HTMLButtonElement) => void;
}

/**
 * The Rewrite/Continue command pair. Only the initiating command
 * carries aria-busy and its pending label; the shared busy flag
 * disables both while any proposal work owns the panel.
 */
export function StudioCopilotProposalCommands({
  busy,
  continueButtonRef,
  onRunCommand,
  pendingOperation,
}: StudioCopilotProposalCommandsProps) {
  const { t } = useTranslation();
  return (
    <div className="studio-inspector__actions">
      <button
        aria-busy={pendingOperation === "rewrite" || undefined}
        className="ui-command"
        disabled={busy}
        onClick={(event) => {
          onRunCommand("rewrite", event.currentTarget);
        }}
        type="button"
      >
        <Sparkles />{" "}
        {pendingOperation === "rewrite"
          ? t("copilot.action.rewriting")
          : t("copilot.action.rewrite")}
      </button>
      <button
        aria-busy={pendingOperation === "continue" || undefined}
        className="ui-command"
        disabled={busy}
        onClick={(event) => {
          onRunCommand("continue", event.currentTarget);
        }}
        ref={continueButtonRef}
        type="button"
      >
        {pendingOperation === "continue"
          ? t("copilot.action.generating")
          : t("copilot.action.continue")}
      </button>
    </div>
  );
}
