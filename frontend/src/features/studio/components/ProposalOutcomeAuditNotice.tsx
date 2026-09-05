import type { ProposalAuditStatus } from "../hooks/useStudioJobs";

interface ProposalOutcomeAuditNoticeProps {
  readonly status: ProposalAuditStatus;
  readonly onRetry?: () => void | Promise<void>;
  readonly onGenerateAnother?: (target: HTMLButtonElement) => void | Promise<void>;
}

export function ProposalOutcomeAuditNotice({
  status,
  onRetry,
  onGenerateAnother,
}: ProposalOutcomeAuditNoticeProps) {
  if (status === "auditing") {
    return (
      <section className="ui-form-error" role="status">
        <p>The proposal outcome is unknown. Checking job history for audit evidence…</p>
      </section>
    );
  }

  if (status === "audit_failed") {
    return (
      <section className="ui-form-error" role="alert">
        <p>
          The proposal outcome is unknown, and job history could not be refreshed. Retry only the
          audit refresh before generating again.
        </p>
        <button className="ui-command" onClick={() => void onRetry?.()} type="button">
          Retry audit refresh
        </button>
      </section>
    );
  }

  return (
    <section className="ui-form-error" role="alert">
      <p>
        The previous proposal may already have been saved. This job-history snapshot cannot confirm
        which job came from that attempt or whether the earlier stream has finished. Generating
        again can create another job and usage event.
      </p>
      <button
        className="ui-command"
        onClick={(event) => void onGenerateAnother?.(event.currentTarget)}
        type="button"
      >
        Generate another proposal
      </button>
    </section>
  );
}
