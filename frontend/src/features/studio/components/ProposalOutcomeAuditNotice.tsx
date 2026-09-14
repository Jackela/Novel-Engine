import { useTranslation } from "@/app/i18n/useTranslation";

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
  const { t } = useTranslation();

  if (status === "auditing") {
    return (
      <section className="ui-form-error" role="status">
        <p>{t("audit.checking")}</p>
      </section>
    );
  }

  if (status === "audit_failed") {
    return (
      <section className="ui-form-error" role="alert">
        <p>{t("audit.failed")}</p>
        <button className="ui-command" onClick={() => void onRetry?.()} type="button">
          {t("audit.action.retryRefresh")}
        </button>
      </section>
    );
  }

  return (
    <section className="ui-form-error" role="alert">
      <p>{t("audit.unknown")}</p>
      <button
        className="ui-command"
        onClick={(event) => void onGenerateAnother?.(event.currentTarget)}
        type="button"
      >
        {t("audit.action.generateAnother")}
      </button>
    </section>
  );
}
