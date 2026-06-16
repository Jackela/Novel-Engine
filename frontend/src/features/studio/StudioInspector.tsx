import {
  Bot,
  Briefcase,
  Check,
  Download,
  History,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  X,
} from 'lucide-react';
import type { Dispatch, FormEvent, SetStateAction } from 'react';

import type { Review, Revision, StudioExport, StudioJob } from '@/app/types/studio';

import type { InspectorTab } from './studioConstants';

export interface SettingsFormState {
  title: string;
  description: string;
  provider: string;
}

interface StudioInspectorProps {
  error: string | null;
  exports: StudioExport[];
  inspector: InspectorTab;
  instruction: string;
  jobs: StudioJob[];
  latestReview: Review | null;
  loadedRevisionId: string | null;
  proposal: StudioJob | null;
  revisions: Revision[];
  settingsForm: SettingsFormState;
  onAcceptProposal: () => void;
  onLoadJobs: () => void;
  onRestoreRevision: (revisionId: string) => void;
  onRetryJob: (jobId: string) => void;
  onRunProposal: (operation: 'continue' | 'rewrite') => void;
  onRunReview: () => void;
  onUpdateSettings: (event: FormEvent) => void;
  setInspector: Dispatch<SetStateAction<InspectorTab>>;
  setInstruction: Dispatch<SetStateAction<string>>;
  setProposal: Dispatch<SetStateAction<StudioJob | null>>;
  setSettingsForm: Dispatch<SetStateAction<SettingsFormState>>;
}

export function StudioInspector({
  error,
  exports,
  inspector,
  instruction,
  jobs,
  latestReview,
  loadedRevisionId,
  proposal,
  revisions,
  settingsForm,
  onAcceptProposal,
  onLoadJobs,
  onRestoreRevision,
  onRetryJob,
  onRunProposal,
  onRunReview,
  onUpdateSettings,
  setInspector,
  setInstruction,
  setProposal,
  setSettingsForm,
}: StudioInspectorProps) {
  return (
    <aside className="studio-inspector">
      <nav className="inspector-tabs">
        <button
          className={inspector === 'copilot' ? 'active' : ''}
          onClick={() => setInspector('copilot')}
          type="button"
        >
          <Bot /> Copilot
        </button>
        <button
          className={inspector === 'review' ? 'active' : ''}
          onClick={() => setInspector('review')}
          type="button"
        >
          <ShieldCheck /> Review
        </button>
        <button
          className={inspector === 'history' ? 'active' : ''}
          onClick={() => setInspector('history')}
          type="button"
        >
          <History /> History
        </button>
        <button
          className={inspector === 'jobs' ? 'active' : ''}
          onClick={() => setInspector('jobs')}
          type="button"
        >
          <Briefcase /> Jobs
        </button>
      </nav>

      {error ? <div className="inspector-error">{error}</div> : null}

      {inspector === 'copilot' ? (
        <div className="inspector-content">
          <h2>AI proposal</h2>
          <p>Copilot never changes the manuscript until you accept a proposal.</p>
          <textarea
            onChange={(event) => setInstruction(event.target.value)}
            placeholder="Describe the change or direction..."
            rows={5}
            value={instruction}
          />
          <div className="inspector-actions">
            <button className="command" onClick={() => onRunProposal('rewrite')} type="button">
              <Sparkles /> Rewrite
            </button>
            <button className="command" onClick={() => onRunProposal('continue')} type="button">
              Continue
            </button>
          </div>
          {proposal?.result.proposal_markdown ? (
            <section className="proposal">
              <header>
                <strong>Proposed Markdown</strong>
                <span>Preview only</span>
              </header>
              <pre>{proposal.result.proposal_markdown}</pre>
              <div className="inspector-actions">
                <button
                  className="command command--primary"
                  onClick={onAcceptProposal}
                  type="button"
                >
                  <Check /> Accept
                </button>
                <button className="command" onClick={() => setProposal(null)} type="button">
                  <X /> Reject
                </button>
              </div>
            </section>
          ) : null}
        </div>
      ) : null}

      {inspector === 'review' ? (
        <div className="inspector-content">
          <header className="inspector-heading">
            <div>
              <h2>Review findings</h2>
              <p>Snapshot-bound and non-mutating.</p>
            </div>
            <button className="icon-command" onClick={onRunReview} title="Run review" type="button">
              <RotateCcw />
            </button>
          </header>
          {latestReview?.issues.length ? (
            latestReview.issues.map((issue) => (
              <article className={`review-issue review-issue--${issue.severity}`} key={issue.id}>
                <header>
                  <strong>{issue.code.replace(/_/g, ' ')}</strong>
                  <span>{issue.severity}</span>
                </header>
                <p>{issue.message}</p>
                <small>{issue.suggestion}</small>
              </article>
            ))
          ) : (
            <p className="empty-panel">No review findings. Run a review when ready.</p>
          )}
        </div>
      ) : null}

      {inspector === 'history' ? (
        <div className="inspector-content">
          <h2>Revision history</h2>
          <p>Restoring creates a new revision and preserves the chain.</p>
          <div className="revision-list">
            {revisions.map((revision) => (
              <article key={revision.id}>
                <div>
                  <strong>{revision.source}</strong>
                  <time>{new Date(revision.created_at).toLocaleString()}</time>
                  <small>
                    {revision.word_count} words · {revision.id.slice(0, 8)}
                  </small>
                </div>
                {revision.id !== loadedRevisionId ? (
                  <button
                    className="icon-command"
                    onClick={() => onRestoreRevision(revision.id)}
                    title="Restore revision"
                    type="button"
                  >
                    <RotateCcw />
                  </button>
                ) : (
                  <span className="current-revision">Current</span>
                )}
              </article>
            ))}
          </div>
          {exports.length ? (
            <>
              <h2>Recent exports</h2>
              {exports.slice(0, 4).map((item) => (
                <a className="export-row" href={item.download_url} key={item.id}>
                  <Download />
                  <span>
                    {item.format.toUpperCase()} · {Math.ceil(item.size_bytes / 1024)} KB
                  </span>
                </a>
              ))}
            </>
          ) : null}
        </div>
      ) : null}

      {inspector === 'settings' ? (
        <form className="inspector-content" onSubmit={onUpdateSettings}>
          <h2>Project settings</h2>
          <label className="settings-field">
            <span>Title</span>
            <input
              maxLength={240}
              onChange={(event) =>
                setSettingsForm((current) => ({ ...current, title: event.target.value }))
              }
              value={settingsForm.title}
            />
          </label>
          <label className="settings-field">
            <span>Description</span>
            <textarea
              maxLength={10000}
              onChange={(event) =>
                setSettingsForm((current) => ({ ...current, description: event.target.value }))
              }
              rows={4}
              value={settingsForm.description}
            />
          </label>
          <label className="settings-field">
            <span>Provider</span>
            <select
              onChange={(event) =>
                setSettingsForm((current) => ({ ...current, provider: event.target.value }))
              }
              value={settingsForm.provider}
            >
              <option value="mock">mock</option>
              <option value="dashscope">dashscope</option>
              <option value="openai_compatible">openai_compatible</option>
            </select>
          </label>
          <div className="settings-field">
            <span>Storage</span>
            <span>SQLite</span>
          </div>
          <div className="settings-field">
            <span>Document syntax</span>
            <span>Markdown</span>
          </div>
          <div className="inspector-actions">
            <button className="command command--primary" type="submit">
              Save settings
            </button>
          </div>
        </form>
      ) : null}

      {inspector === 'jobs' ? (
        <div className="inspector-content">
          <header className="inspector-heading">
            <div>
              <h2>Jobs</h2>
              <p>Durable operation status.</p>
            </div>
            <button
              className="icon-command"
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
      ) : null}
    </aside>
  );
}
