import { RotateCcw } from "lucide-react";
import { useRef, useState } from "react";

import { api } from "@/app/api";
import { formatDateTime } from "@/app/i18n/format";
import { useTranslation } from "@/app/i18n/useTranslation";
import type { StudioJobSummary } from "@/app/types/studio";
import { toErrorMessage } from "../hooks/toErrorMessage";
import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";
import type { JobsLoadInitiator } from "../hooks/useStudioJobs";
import { providerLabel } from "../studioConstants";

interface StudioJobsPanelProps {
  jobs: StudioJobSummary[];
  /** DR-010: project scope for lazily reading a discarded proposal's text. */
  projectId: string;
  hasOlderJobs?: boolean;
  onLoadJobs: () => void | Promise<void>;
  onLoadOlderJobs?: () => void | Promise<void>;
  onRetryJob: (jobId: string) => void | Promise<void>;
  isLoading?: boolean;
  loadingInitiator?: JobsLoadInitiator | null;
  retryingJobId?: string | null;
  retryGated?: boolean;
}

interface ViewedProposalText {
  readonly jobId: string;
  readonly text: string | null;
  readonly error: string | null;
}

export function StudioJobsPanel({
  jobs,
  projectId,
  hasOlderJobs = false,
  onLoadJobs,
  onLoadOlderJobs = () => undefined,
  onRetryJob,
  isLoading = false,
  loadingInitiator = null,
  retryingJobId = null,
  retryGated = false,
}: StudioJobsPanelProps) {
  const isBusy = isLoading || retryingJobId !== null || retryGated;
  const refreshIsInitiator = isLoading && loadingInitiator === "refresh";
  const olderIsInitiator = isLoading && loadingInitiator === "load_older";
  const { t } = useTranslation();
  const runWithFocusRestoration = useCommandFocusRestoration(isBusy);
  const refreshButtonRef = useRef<HTMLButtonElement>(null);
  // DR-010: a completed proposal's text stays readable even after the panel
  // cleared it — the job detail read is lazy, scoped, and copy-friendly.
  const [viewedProposal, setViewedProposal] = useState<ViewedProposalText | null>(null);

  const viewProposalText = async (jobId: string): Promise<void> => {
    setViewedProposal({ jobId, text: null, error: null });
    try {
      const detail = await api.job(projectId, jobId, {});
      setViewedProposal({ jobId, text: detail.result.proposal_markdown ?? "", error: null });
    } catch (reason) {
      setViewedProposal({
        jobId,
        text: null,
        error: toErrorMessage(reason, t("jobs.proposal.error")),
      });
    }
  };

  return (
    <div aria-busy={isBusy} className="studio-inspector__panel">
      <header className="studio-inspector__heading">
        <div>
          <h2>{t("jobs.heading")}</h2>
          <p>{t("jobs.hint")}</p>
        </div>
        <button
          aria-busy={refreshIsInitiator || undefined}
          aria-label={refreshIsInitiator ? t("jobs.action.refreshing") : t("jobs.action.refresh")}
          className="ui-command--icon"
          disabled={isBusy}
          onClick={(event) => {
            void runWithFocusRestoration(event.currentTarget, onLoadJobs);
          }}
          ref={refreshButtonRef}
          title={t("jobs.action.refresh")}
          type="button"
        >
          <RotateCcw />
        </button>
      </header>
      {jobs.length ? (
        <div className="studio-inspector__revision-list">
          {jobs.map((job) => (
            <article key={job.id}>
              <div>
                <strong>{job.operation}</strong>
                <span className={`job-status job-status--${job.status}`}>{job.status}</span>
                <small>
                  {t("jobs.row.meta", {
                    provider: providerLabel(job.provider),
                    date: formatDateTime(job.created_at),
                  })}
                </small>
                {job.error ? (
                  // DR-021: the server's raw failure report is English and may
                  // quote provider HTTP details, so it lives behind a
                  // collapsed disclosure while the visible line stays
                  // localized.
                  <div className="job-error">
                    <small className="job-error__primary">{t("jobs.error.failed")}</small>
                    <details className="job-error__details">
                      <summary>{t("jobs.error.technicalDetails")}</summary>
                      <small>{job.error}</small>
                    </details>
                  </div>
                ) : null}
              </div>
              {job.kind !== "import" &&
              (job.status === "failed" || job.status === "interrupted") ? (
                <button
                  aria-busy={retryingJobId === job.id}
                  aria-label={
                    retryingJobId === job.id
                      ? t("jobs.action.retrying", { operation: job.operation })
                      : t("jobs.action.retry", { operation: job.operation })
                  }
                  className="ui-command--icon"
                  disabled={isBusy}
                  onClick={(event) => {
                    void runWithFocusRestoration(
                      event.currentTarget,
                      () => onRetryJob(job.id),
                      () => refreshButtonRef.current,
                    );
                  }}
                  title={t("jobs.action.retryTitle")}
                  type="button"
                >
                  <RotateCcw />
                </button>
              ) : null}
              {job.kind === "proposal" && job.status === "completed" ? (
                <button
                  className="ui-command"
                  onClick={(event) => {
                    void runWithFocusRestoration(
                      event.currentTarget,
                      () => viewProposalText(job.id),
                      () => refreshButtonRef.current,
                    );
                  }}
                  type="button"
                >
                  {t("jobs.proposal.view")}
                </button>
              ) : null}
              {viewedProposal?.jobId === job.id ? (
                <div className="studio-inspector__proposal">
                  {viewedProposal.error !== null ? (
                    <p role="alert">{viewedProposal.error}</p>
                  ) : viewedProposal.text !== null ? (
                    <>
                      <pre>{viewedProposal.text}</pre>
                      <button
                        className="ui-command"
                        onClick={() => {
                          void navigator.clipboard.writeText(viewedProposal.text ?? "");
                        }}
                        type="button"
                      >
                        {t("jobs.proposal.copy")}
                      </button>
                    </>
                  ) : (
                    <p role="status">{t("jobs.proposal.loading")}</p>
                  )}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      ) : (
        <p className="studio-inspector__empty">{t("jobs.empty")}</p>
      )}
      {hasOlderJobs ? (
        <button
          aria-busy={olderIsInitiator || undefined}
          className="ui-command"
          disabled={isBusy}
          onClick={(event) => {
            void runWithFocusRestoration(
              event.currentTarget,
              onLoadOlderJobs,
              () => refreshButtonRef.current,
            );
          }}
          type="button"
        >
          {olderIsInitiator ? t("jobs.action.loadingOlder") : t("jobs.action.loadOlder")}
        </button>
      ) : null}
    </div>
  );
}
