import { RotateCcw } from "lucide-react";
import { useRef } from "react";

import type { StudioJob } from "@/app/types/studio";
import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";
import type { JobsLoadInitiator } from "../hooks/useStudioJobs";

interface StudioJobsPanelProps {
  jobs: StudioJob[];
  onLoadJobs: () => void | Promise<void>;
  onRetryJob: (jobId: string) => void | Promise<void>;
  isLoading?: boolean;
  loadingInitiator?: JobsLoadInitiator | null;
  retryingJobId?: string | null;
  retryGated?: boolean;
}

export function StudioJobsPanel({
  jobs,
  onLoadJobs,
  onRetryJob,
  isLoading = false,
  loadingInitiator = null,
  retryingJobId = null,
  retryGated = false,
}: StudioJobsPanelProps) {
  const isBusy = isLoading || retryingJobId !== null || retryGated;
  const refreshIsInitiator = isLoading && loadingInitiator === "refresh";
  const runWithFocusRestoration = useCommandFocusRestoration(isBusy);
  const refreshButtonRef = useRef<HTMLButtonElement>(null);

  return (
    <div aria-busy={isBusy} className="studio-inspector__panel">
      <header className="studio-inspector__heading">
        <div>
          <h2>Jobs</h2>
          <p>Durable operation status.</p>
        </div>
        <button
          aria-busy={refreshIsInitiator || undefined}
          aria-label={refreshIsInitiator ? "Refreshing jobs" : "Refresh jobs"}
          className="ui-command--icon"
          disabled={isBusy}
          onClick={(event) => {
            void runWithFocusRestoration(event.currentTarget, onLoadJobs);
          }}
          ref={refreshButtonRef}
          title="Refresh jobs"
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
                  {job.provider} · {new Date(job.created_at).toLocaleString()}
                </small>
                {job.error ? <small className="job-error">{job.error}</small> : null}
              </div>
              {job.status === "failed" || job.status === "interrupted" ? (
                <button
                  aria-busy={retryingJobId === job.id}
                  aria-label={
                    retryingJobId === job.id
                      ? `Retrying ${job.operation}`
                      : `Retry ${job.operation}`
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
                  title="Retry job"
                  type="button"
                >
                  <RotateCcw />
                </button>
              ) : null}
            </article>
          ))}
        </div>
      ) : (
        <p className="studio-inspector__empty">No jobs yet.</p>
      )}
    </div>
  );
}
