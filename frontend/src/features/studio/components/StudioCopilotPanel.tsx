import { Check, Copy, RotateCcw, Sparkles, X } from "lucide-react";
import { type Dispatch, type SetStateAction, useRef, useState } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";
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
  /** DR-006: the stream failed mid-flight; `streamingText` is the preserved partial text. */
  streamingInterrupted?: boolean;
  /** DR-010: the author stopped the stream; `streamingText` is the kept partial text. */
  streamingStopped?: boolean;
  /** #308: stops this client from observing the running stream. */
  onStopProposal?: () => void | Promise<void>;
  /** DR-010: the one-shot undo for the most recent committed acceptance, when offered. */
  acceptanceUndo?: { readonly onUndo: () => void | Promise<void> } | null;
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
  streamingInterrupted = false,
  streamingStopped = false,
  onStopProposal,
  acceptanceUndo = null,
  proposalOutcomeUnknown = false,
  proposalAuditStatus = "idle",
  unknownAttemptOperation = "continue",
  onRetryProposalAudit,
}: StudioCopilotPanelProps) {
  const { t } = useTranslation();
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
  /** DR-006/DR-010: a settled stream keeps its received text readable. */
  const streamTextKept = streamingInterrupted || streamingStopped;
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

  const copyStreamedText = () => {
    if (streamingText === null) return;
    void navigator.clipboard.writeText(streamingText);
  };

  return (
    <div aria-busy={isBusy} className="studio-inspector__panel">
      <h2>{t("copilot.heading")}</h2>
      <p>{t("copilot.hint.guard")}</p>
      <p>{t("copilot.hint.flow")}</p>
      <textarea
        aria-label={t("copilot.field.instruction")}
        disabled={isBusy || (proposalOutcomeUnknown && proposalAuditStatus !== "audit_succeeded")}
        onChange={(event) => setInstruction(event.target.value)}
        placeholder={t("copilot.placeholder.example")}
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
            <Sparkles />{" "}
            {pendingProposalOperation === "rewrite"
              ? t("copilot.action.rewriting")
              : t("copilot.action.rewrite")}
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
            {pendingProposalOperation === "continue"
              ? t("copilot.action.generating")
              : t("copilot.action.continue")}
          </button>
        </div>
      )}
      {acceptanceUndo ? (
        <>
          <p aria-live="polite">{t("copilot.undo.body")}</p>
          <div className="studio-inspector__actions">
            <button
              className="ui-command"
              onClick={(event) => {
                void runWithFocusRestoration(
                  event.currentTarget,
                  acceptanceUndo.onUndo,
                  () => continueButtonRef.current ?? instructionRef.current,
                );
              }}
              type="button"
            >
              <RotateCcw /> {t("copilot.action.undo")}
            </button>
          </div>
        </>
      ) : null}
      {isStreaming ? (
        <section
          aria-busy={streamTextKept ? undefined : true}
          className="studio-inspector__proposal"
        >
          <header>
            <strong>{t("copilot.proposal.heading")}</strong>
            <span>
              {streamingInterrupted
                ? t("copilot.proposal.interrupted")
                : streamingStopped
                  ? t("copilot.proposal.stopped")
                  : t("copilot.proposal.streaming")}
            </span>
          </header>
          <pre aria-live="polite">{streamingText}</pre>
          <div className="studio-inspector__actions">
            {streamTextKept ? (
              <button className="ui-command" onClick={copyStreamedText} type="button">
                <Copy /> {t("copilot.action.copy")}
              </button>
            ) : (
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
                <X /> {t("copilot.action.stop")}
              </button>
            )}
          </div>
        </section>
      ) : proposal?.result.proposal_markdown ? (
        <section className="studio-inspector__proposal">
          <header>
            <strong>{t("copilot.proposal.heading")}</strong>
            <span>{t("copilot.proposal.previewOnly")}</span>
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
              <Check /> {t("copilot.action.accept")}
            </button>
            <button
              className="ui-command"
              disabled={isBusy}
              onClick={() => setProposal(null)}
              type="button"
            >
              <X /> {t("copilot.action.reject")}
            </button>
          </div>
        </section>
      ) : null}
    </div>
  );
}
