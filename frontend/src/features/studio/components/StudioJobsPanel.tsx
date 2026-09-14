import { RotateCcw } from "lucide-react";
import { useRef } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";
import type { StudioJobSummary } from "@/app/types/studio";
import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";
import type { JobsLoadInitiator } from "../hooks/useStudioJobs";
import { providerLabel } from "../studioConstants";

interface StudioJobsPanelProps {
  jobs: StudioJobSummary[];
  hasOlderJobs?: boolean;
  onLoadJobs: () => void | Promise<void>;
  onLoadOlderJobs?: () => void | Promise<void>;
  onRetryJob: (jobId: string) => void | Promise<void>;
  isLoading?: boolean;
  loadingInitiator?: JobsLoadInitiator | null;
  retryingJobId?: string | null;
  retryGated?: boolean;
}

export function StudioJobsPanel({
  jobs,
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
                    date: new Date(job.created_at).toLocaleString(),
                  })}
                </small>
                {job.error ? <small className="job-error">{job.error}</small> : null}
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
