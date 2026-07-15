import { RotateCcw } from 'lucide-react';

import type { StudioJob } from '@/app/types/studio';

interface StudioJobsPanelProps {
  jobs: StudioJob[];
  onLoadJobs: () => void;
  onRetryJob: (jobId: string) => void;
  isLoading?: boolean;
  retryingJobId?: string | null;
}

export function StudioJobsPanel({
  jobs,
  onLoadJobs,
  onRetryJob,
  isLoading = false,
  retryingJobId = null,
}: StudioJobsPanelProps) {
  const isBusy = isLoading || retryingJobId !== null;

  return (
    <div aria-busy={isBusy} className="inspector-content">
      <header className="inspector-heading">
        <div>
          <h2>Jobs</h2>
          <p>Durable operation status.</p>
        </div>
        <button
          aria-busy={isLoading}
          aria-label={isLoading ? 'Refreshing jobs' : 'Refresh jobs'}
          className="icon-command"
          disabled={isBusy}
          onClick={onLoadJobs}
          title="Refresh jobs"
          type="button"
        >
          <RotateCcw />
        </button>
      </header>
      {jobs.length ? (
        <div className="revision-list">
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
              {job.status === 'failed' || job.status === 'interrupted' ? (
                <button
                  aria-busy={retryingJobId === job.id}
                  aria-label={
                    retryingJobId === job.id
                      ? `Retrying ${job.operation}`
                      : `Retry ${job.operation}`
                  }
                  className="icon-command"
                  disabled={isBusy}
                  onClick={() => onRetryJob(job.id)}
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
        <p className="empty-panel">No jobs yet.</p>
      )}
    </div>
  );
}
