import { RotateCcw } from 'lucide-react';

import type { StudioJob } from '@/app/types/studio';

interface StudioJobsPanelProps {
  jobs: StudioJob[];
  onLoadJobs: () => void;
  onRetryJob: (jobId: string) => void;
}

export function StudioJobsPanel({ jobs, onLoadJobs, onRetryJob }: StudioJobsPanelProps) {
  return (
    <div className="inspector-content">
      <header className="inspector-heading">
        <div>
          <h2>Jobs</h2>
          <p>Durable operation status.</p>
        </div>
        <button className="icon-command" onClick={onLoadJobs} title="Refresh jobs" type="button">
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
                  className="icon-command"
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
