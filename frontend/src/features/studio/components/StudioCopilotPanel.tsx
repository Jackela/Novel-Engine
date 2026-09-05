import { Check, Sparkles, X } from "lucide-react";
import { type Dispatch, type SetStateAction, useRef, useState } from "react";

import type { StudioJob } from "@/app/types/studio";
import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";
import type { ProposalAuditStatus } from "../hooks/useStudioJobs";
import { ProposalOutcomeAuditNotice } from "./ProposalOutcomeAuditNotice";

interface StudioCopilotPanelProps {
  instruction: string;
  setInstruction: Dispatch<SetStateAction<string>>;
  proposal: StudioJob | null;
  setProposal: Dispatch<SetStateAction<StudioJob | null>>;
  onRunProposal: (operation: "continue" | "rewrite") => void | Promise<void>;
  onAcceptProposal: () => void | Promise<void>;
  /** True while a proposal request is in flight. */
  isRunningProposal?: boolean;
  /** True while accepting the currently displayed proposal. */
  isAcceptingProposal?: boolean;
  /** #308: markdown received so far while the proposal stream is running. */
  streamingText?: string | null;
  /** #308: stops this client from observing the running stream. */
  onStopProposal?: () => void | Promise<void>;
  proposalOutcomeUnknown?: boolean;
  proposalAuditStatus?: ProposalAuditStatus;
  unknownAttemptOperation?: "continue" | "rewrite";
  onRetryProposalAudit?: () => void | Promise<void>;
}

export function StudioCopilotPanel({
  instruction,
  setInstruction,
  proposal,
  setProposal,
  onRunProposal,
  onAcceptProposal,
  isRunningProposal = false,
  isAcceptingProposal = false,
  streamingText = null,
  onStopProposal,
  proposalOutcomeUnknown = false,
  proposalAuditStatus = "idle",
  unknownAttemptOperation = "continue",
  onRetryProposalAudit,
}: StudioCopilotPanelProps) {
  const pendingProposalOperationRef = useRef<"continue" | "rewrite" | null>(null);
  const [pendingProposalOperation, setPendingProposalOperation] = useState<
    "continue" | "rewrite" | null
  >(null);
  const isBusy =
    isRunningProposal ||
    isAcceptingProposal ||
    pendingProposalOperation !== null ||
    proposalAuditStatus === "auditing";
  const isStreaming = streamingText !== null;
  const runWithFocusRestoration = useCommandFocusRestoration(isBusy);
  const instructionRef = useRef<HTMLTextAreaElement>(null);
  const continueButtonRef = useRef<HTMLButtonElement>(null);

  const runProposalCommand = (operation: "continue" | "rewrite", target: HTMLButtonElement) => {
    if (isBusy || pendingProposalOperationRef.current !== null) return;
    pendingProposalOperationRef.current = operation;
    setPendingProposalOperation(operation);
    void runWithFocusRestoration(
      target,
      async () => {
        try {
          await onRunProposal(operation);
        } finally {
          if (pendingProposalOperationRef.current === operation) {
            pendingProposalOperationRef.current = null;
          }
          setPendingProposalOperation((current) => (current === operation ? null : current));
        }
      },
      () =>
        operation === "rewrite"
          ? (instructionRef.current ?? continueButtonRef.current)
          : (continueButtonRef.current ?? instructionRef.current),
    );
  };

  return (
    <div aria-busy={isBusy} className="studio-inspector__panel">
      <h2>AI proposal</h2>
      <p>Copilot never changes the manuscript until you accept a proposal.</p>
      <textarea
        aria-label="Proposal instruction"
        disabled={isBusy || (proposalOutcomeUnknown && proposalAuditStatus !== "audit_succeeded")}
        onChange={(event) => setInstruction(event.target.value)}
        placeholder="Describe the change or direction..."
        ref={instructionRef}
        rows={5}
        value={instruction}
      />
      {proposalOutcomeUnknown ? (
        <ProposalOutcomeAuditNotice
          onGenerateAnother={(target) => runProposalCommand(unknownAttemptOperation, target)}
          onRetry={onRetryProposalAudit}
          status={proposalAuditStatus}
        />
      ) : (
        <div className="studio-inspector__actions">
          <button
            aria-busy={pendingProposalOperation === "rewrite" || undefined}
            className="ui-command"
            disabled={isBusy}
            onClick={(event) => {
              runProposalCommand("rewrite", event.currentTarget);
            }}
            type="button"
          >
            <Sparkles /> {pendingProposalOperation === "rewrite" ? "Rewriting…" : "Rewrite"}
          </button>
          <button
            aria-busy={pendingProposalOperation === "continue" || undefined}
            className="ui-command"
            disabled={isBusy}
            onClick={(event) => {
              runProposalCommand("continue", event.currentTarget);
            }}
            ref={continueButtonRef}
            type="button"
          >
            {pendingProposalOperation === "continue" ? "Generating…" : "Continue"}
          </button>
        </div>
      )}
      {isStreaming ? (
        <section aria-busy="true" className="studio-inspector__proposal">
          <header>
            <strong>Proposed Markdown</strong>
            <span>Streaming…</span>
          </header>
          <pre aria-live="polite">{streamingText}</pre>
          <div className="studio-inspector__actions">
            <button
              className="ui-command"
              onClick={(event) => {
                if (onStopProposal) {
                  void runWithFocusRestoration(
                    event.currentTarget,
                    onStopProposal,
                    () => continueButtonRef.current ?? instructionRef.current,
                  );
                }
              }}
              type="button"
            >
              <X /> Stop
            </button>
          </div>
        </section>
      ) : proposal?.result.proposal_markdown ? (
        <section className="studio-inspector__proposal">
          <header>
            <strong>Proposed Markdown</strong>
            <span>Preview only</span>
          </header>
          <pre>{proposal.result.proposal_markdown}</pre>
          <div className="studio-inspector__actions">
            <button
              aria-busy={isAcceptingProposal}
              className="ui-command ui-command--primary"
              disabled={isBusy}
              onClick={(event) => {
                void runWithFocusRestoration(
                  event.currentTarget,
                  onAcceptProposal,
                  () => instructionRef.current ?? continueButtonRef.current,
                );
              }}
              type="button"
            >
              <Check /> Accept
            </button>
            <button
              className="ui-command"
              disabled={isBusy}
              onClick={() => setProposal(null)}
              type="button"
            >
              <X /> Reject
            </button>
          </div>
        </section>
      ) : null}
    </div>
  );
}
