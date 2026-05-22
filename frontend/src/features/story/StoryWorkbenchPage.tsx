import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import type { SessionState, WorkspaceSurfaceView } from '@/app/types/auth';
import type {
  StoryGenre,
  ProviderName,
  ReviewIssue,
  WorkspaceCreateRequest,
  WorkspaceJob,
} from '@/app/types/story';
import { Button } from '@/components/Button';
import { Panel } from '@/components/Panel';
import { StatusPill } from '@/components/StatusPill';
import { useAuth } from '@/features/auth/useAuth';

import { useStoryWorkbench } from './useStoryWorkbench';

const STORY_GENRES: StoryGenre[] = [
  'fantasy',
  'sci-fi',
  'mystery',
  'romance',
  'horror',
  'adventure',
  'historical',
  'thriller',
  'comedy',
  'drama',
];

interface ComposerState {
  title: string;
  genre: StoryGenre;
  premise: string;
  targetChapters: number;
  targetAudience: string;
  themes: string;
  tone: string;
}

const initialComposerState: ComposerState = {
  title: '',
  genre: 'fantasy',
  premise: '',
  targetChapters: 3,
  targetAudience: '',
  themes: '',
  tone: 'immersive serial fiction',
};

function normalizeView(value: string | null | undefined): WorkspaceSurfaceView {
  return value === 'playback' ? 'playback' : 'workspace';
}

function parseThemes(rawThemes: string): string[] {
  return rawThemes.split(',').map((theme) => theme.trim()).filter(Boolean);
}

function formatDate(value: string | undefined | null): string {
  if (!value) return 'Unknown';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function buildPayload(formState: ComposerState): WorkspaceCreateRequest {
  return {
    title: formState.title.trim(),
    genre: formState.genre,
    premise: formState.premise.trim(),
    target_chapters: formState.targetChapters,
    target_audience: formState.targetAudience.trim() || null,
    themes: parseThemes(formState.themes),
    tone: formState.tone.trim() || 'immersive serial fiction',
  };
}

function buildStudioLocation(session: SessionState) {
  const params = new URLSearchParams();
  if (session.lastWorkspaceId) params.set('workspace', session.lastWorkspaceId);
  if (session.lastJobId) params.set('job', session.lastJobId);
  params.set('view', session.lastView ?? 'workspace');
  const query = params.toString();
  return query ? `/studio?${query}` : '/studio';
}

function jobLabel(job: WorkspaceJob | null): string {
  if (!job) return 'Waiting for a workspace action';
  if (job.status === 'failed') return `${job.operation} failed: ${job.error ?? 'unknown error'}`;
  if (job.status === 'interrupted') return `${job.operation} interrupted`;
  return `${job.operation} ${job.status}`;
}

function formatActionError(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function jobTone(job: WorkspaceJob | null) {
  if (!job) return 'idle' as const;
  if (job.status === 'failed' || job.status === 'interrupted') return 'offline' as const;
  if (job.status === 'completed') return 'healthy' as const;
  return 'running' as const;
}

function reviewTone(blocked: boolean) {
  return blocked ? 'degraded' : 'healthy';
}

function issueList(issues: ReviewIssue[]) {
  if (issues.length === 0) {
    return <li className="studio-empty">No items recorded.</li>;
  }

  return issues.map((issue) => (
    <li key={`${issue.code}-${issue.location}-${issue.message}`} className="studio-chapter-card">
      <div className="studio-chapter-card__header">
        <strong>{issue.code}</strong>
        <span>{issue.severity}</span>
      </div>
      <p>{issue.message}</p>
      <p>{issue.suggestion}</p>
    </li>
  ));
}

function renderSessionSummary(session: SessionState, workspaceSummary: string) {
  const sessionTitle =
    session.kind === 'user'
      ? session.user?.name ?? 'Signed-in author'
      : session.activeWorkspace?.label ?? 'Guest workspace';
  const sessionMeta =
    session.kind === 'user' ? session.user?.email ?? session.workspaceId : session.workspaceId;

  return (
    <div className="studio-session-card" data-testid="studio-session-summary">
      <StatusPill tone={session.kind === 'guest' ? 'idle' : 'running'}>
        {session.kind === 'guest' ? 'guest session' : 'signed in'}
      </StatusPill>
      <h3>{sessionTitle}</h3>
      <p>{workspaceSummary}</p>
      <dl className="studio-stats studio-stats--compact" data-testid="workspace-switcher">
        <div>
          <dt>Workspace</dt>
          <dd>{session.workspaceId}</dd>
        </div>
        <div>
          <dt>Identity</dt>
          <dd>{sessionMeta}</dd>
        </div>
      </dl>
    </div>
  );
}

export function StoryWorkbenchPage() {
  const auth = useAuth();
  const session = auth.session;

  if (!session) return null;

  return <StoryWorkbenchContent auth={auth} session={session} />;
}

interface StoryWorkbenchContentProps {
  auth: ReturnType<typeof useAuth>;
  session: SessionState;
}

function StoryWorkbenchContent({ auth, session }: StoryWorkbenchContentProps) {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [formState, setFormState] = useState<ComposerState>(initialComposerState);
  const [provider, setProvider] = useState<ProviderName>('mock');
  const [pageError, setPageError] = useState<string | null>(null);
  const sessions = auth.sessions ?? [];
  const activeSessionId = auth.activeSessionId ?? null;

  const preferredWorkspaceId =
    searchParams.get('workspace') ?? session.lastWorkspaceId ?? null;
  const preferredJobId = searchParams.get('job') ?? session.lastJobId ?? null;
  const preferredView = normalizeView(searchParams.get('view') ?? session.lastView ?? 'workspace');

  const workbench = useStoryWorkbench({
    authorId: session.workspaceId,
    enabled: true,
    preferredWorkspaceId,
    preferredJobId,
    onSelectionChange: ({ workspaceId, jobId, view }) => {
      auth.updateSessionSelection({
        lastWorkspaceId: workspaceId,
        lastJobId: jobId,
        lastView: view,
      });
      const params = new URLSearchParams(searchParams);
      if (workspaceId) params.set('workspace', workspaceId);
      else params.delete('workspace');
      if (jobId) params.set('job', jobId);
      else params.delete('job');
      params.set('view', view);
      setSearchParams(params, { replace: true });
    },
  });

  useEffect(() => {
    setProvider(workbench.defaultProvider);
  }, [workbench.defaultProvider]);

  const availableSessions = useMemo(
    () => sessions.filter((entry) => entry.id !== activeSessionId).slice(0, 4),
    [activeSessionId, sessions],
  );
  const workspace = workbench.workspace;
  const providerOptions = workbench.providers.length
    ? workbench.providers
    : [
        {
          provider: 'mock' as const,
          label: 'mock offline demo',
          configured: true,
          is_default: true,
          model: 'deterministic-story-v1',
        },
      ];
  const review = workspace?.latest_review ?? null;
  const currentView = workbench.currentJob ? 'playback' : preferredView;
  const workspaceSummary =
    (workspace ? `${workspace.workspace_id} / ${workspace.chapters.length} chapter(s)` : null) ??
    session.activeWorkspace?.summary ??
    'Local-first writing workspace with Markdown chapters as the manuscript authority.';

  const setQuerySelection = (
    workspaceId: string | null,
    jobId: string | null,
    view: WorkspaceSurfaceView,
  ) => {
    const params = new URLSearchParams(searchParams);
    if (workspaceId) params.set('workspace', workspaceId);
    else params.delete('workspace');
    if (jobId) params.set('job', jobId);
    else params.delete('job');
    params.set('view', view);
    setSearchParams(params, { replace: true });
  };

  const createWorkspace = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPageError(null);
    try {
      const nextWorkspace = await workbench.createWorkspace(buildPayload(formState));
      setQuerySelection(nextWorkspace.workspace_id, null, 'workspace');
    } catch (error) {
      setPageError(formatActionError(error, 'Unable to create the workspace.'));
    }
  };

  const runWorkspace = async () => {
    setPageError(null);
    try {
      const job = await workbench.runJob('run', {
        target_chapters: formState.targetChapters,
        provider,
      });
      setQuerySelection(workbench.activeWorkspaceId, job.job_id, 'playback');
    } catch (error) {
      setPageError(formatActionError(error, 'Unable to run the workspace.'));
    }
  };

  const runSingleJob = async (
    operation: 'draft' | 'review' | 'revise' | 'export',
  ) => {
    setPageError(null);
    try {
      const job = await workbench.runJob(operation, { provider });
      setQuerySelection(workbench.activeWorkspaceId, job.job_id, 'playback');
    } catch (error) {
      setPageError(formatActionError(error, `Unable to run ${operation}.`));
    }
  };

  const switchToSavedSession = async (sessionId: string) => {
    setPageError(null);
    try {
      const nextSession = await auth.switchSession(sessionId);
      navigate(buildStudioLocation(nextSession));
    } catch (error) {
      setPageError(formatActionError(error, 'Unable to switch session.'));
    }
  };

  const leaveCurrentSession = () => {
    auth.signOut();
    navigate('/');
  };

  return (
    <main className="studio-workbench" data-testid="studio-workbench-page">
      <header className="studio-workbench__hero">
        <div className="studio-workbench__hero-copy">
          <p className="studio-workbench__eyebrow">Novel Engine / Local Workspace</p>
          <h1 className="studio-workbench__title">
            {workspace ? workspace.story.title : 'Create or resume a local manuscript'}
          </h1>
          <p className="studio-workbench__summary">
            Markdown chapters are the source of truth. Runs, sidecars, reviews, and exports are
            local artifacts attached to the workspace.
          </p>
        </div>

        <div className="studio-workbench__hero-meta">
          <StatusPill tone={session.kind === 'guest' ? 'idle' : 'running'}>
            {session.kind === 'guest' ? 'guest session' : 'signed in'}
          </StatusPill>
          <span data-testid="export-gate-badge">
            <StatusPill tone={reviewTone(Boolean(review?.export_blocked))}>
              {review?.export_blocked ? 'blockers open' : 'export allowed'}
            </StatusPill>
          </span>
          <span className="studio-workbench__workspace" data-testid="workspace-badge">
            {session.workspaceId}
          </span>
        </div>
      </header>

      {workbench.error || pageError ? (
        <p className="form-error">{workbench.error ?? pageError}</p>
      ) : null}

      <section className="studio-workbench__layout studio-workbench__layout--guided">
        <div className="studio-workbench__column">
          <Panel title="Session / Entry" eyebrow="Rail" testId="studio-session-panel">
            {renderSessionSummary(session, workspaceSummary)}
            <div className="studio-workflow__actions">
              <Link className="button button--secondary" to="/" data-testid="studio-back-to-landing">
                Back to landing
              </Link>
              <Button variant="ghost" onClick={leaveCurrentSession}>
                Sign out
              </Button>
            </div>

            {availableSessions.length ? (
              <div className="studio-notes" data-testid="session-switcher">
                <h3>Switch session</h3>
                <ul className="studio-list">
                  {availableSessions.map((entry) => (
                    <li key={entry.id} className="studio-card">
                      <button
                        className="studio-card__button"
                        type="button"
                        onClick={() => void switchToSavedSession(entry.id)}
                      >
                        <div className="studio-card__header">
                          <strong>{entry.activeWorkspace?.label ?? entry.workspaceId}</strong>
                          <span>{entry.kind}</span>
                        </div>
                        <p className="studio-card__meta">
                          {entry.user?.email ?? entry.workspaceId}
                        </p>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </Panel>

          <Panel
            title="Workspaces"
            eyebrow="Local"
            actions={
              <Button
                variant="ghost"
                onClick={() => void workbench.refreshLibrary()}
                disabled={workbench.isLoading || workbench.isBusy}
              >
                {workbench.isLoading ? 'Refreshing...' : 'Refresh'}
              </Button>
            }
            testId="studio-library-panel"
          >
            <div className="studio-library-summary" data-testid="studio-library-summary">
              <strong>{workbench.workspaces.length} workspace(s)</strong>
              <span>
                {workspace ? `Viewing ${workspace.story.title}` : 'Create or select a workspace.'}
              </span>
            </div>
            <ul className="studio-list" data-testid="studio-list">
              {workbench.workspaces.length === 0 ? (
                <li className="studio-empty">No local workspaces yet.</li>
              ) : (
                workbench.workspaces.map((item) => (
                  <li
                    key={item.workspace_id}
                    className={`studio-card${
                      item.workspace_id === workbench.activeWorkspaceId ? ' studio-card--active' : ''
                    }`}
                  >
                    <button
                      className="studio-card__button"
                      type="button"
                      disabled={workbench.isBusy}
                      onClick={() => void workbench.selectWorkspace(item.workspace_id)}
                      data-testid={`studio-item-${item.workspace_id}`}
                    >
                      <div className="studio-card__header">
                        <strong>{item.story.title}</strong>
                        <span>{item.chapters.length} chapters</span>
                      </div>
                      <p className="studio-card__meta">
                        {item.story.genre} / {item.latest_review?.export_blocked ? 'blocked' : 'reviewable'}
                      </p>
                    </button>
                  </li>
                ))
              )}
            </ul>
          </Panel>

          <Panel title="New workspace" eyebrow="Create" testId="studio-create-panel">
            <form className="studio-form" onSubmit={createWorkspace} data-testid="studio-create-form">
              <label className="field">
                <span>Title</span>
                <input
                  data-testid="studio-title-input"
                  value={formState.title}
                  onChange={(event) =>
                    setFormState((current) => ({ ...current, title: event.target.value }))
                  }
                  required
                />
              </label>
              <label className="field">
                <span>Genre</span>
                <select
                  data-testid="studio-genre-select"
                  value={formState.genre}
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      genre: event.target.value as StoryGenre,
                    }))
                  }
                >
                  {STORY_GENRES.map((genre) => (
                    <option key={genre} value={genre}>
                      {genre}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Premise</span>
                <textarea
                  data-testid="studio-premise-input"
                  value={formState.premise}
                  onChange={(event) =>
                    setFormState((current) => ({ ...current, premise: event.target.value }))
                  }
                  rows={5}
                  required
                />
              </label>
              <div className="studio-form__grid">
                <label className="field">
                  <span>Target chapters</span>
                  <input
                    data-testid="studio-target-chapters-input"
                    type="number"
                    min={1}
                    max={120}
                    value={formState.targetChapters}
                    onChange={(event) =>
                      setFormState((current) => ({
                        ...current,
                        targetChapters: Number(event.target.value),
                      }))
                    }
                    required
                  />
                </label>
                <label className="field">
                  <span>Audience</span>
                  <input
                    data-testid="studio-audience-input"
                    value={formState.targetAudience}
                    onChange={(event) =>
                      setFormState((current) => ({
                        ...current,
                        targetAudience: event.target.value,
                      }))
                    }
                  />
                </label>
              </div>
              <label className="field">
                <span>Provider</span>
                <select
                  data-testid="studio-provider-select"
                  value={provider}
                  onChange={(event) => setProvider(event.target.value as ProviderName)}
                >
                  {providerOptions.map((item) => (
                    <option
                      key={item.provider}
                      value={item.provider}
                      disabled={!item.configured}
                    >
                      {item.label}
                      {item.configured ? '' : ' (not configured)'}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Themes</span>
                <input
                  data-testid="studio-themes-input"
                  value={formState.themes}
                  onChange={(event) =>
                    setFormState((current) => ({ ...current, themes: event.target.value }))
                  }
                />
              </label>
              <label className="field">
                <span>Tone</span>
                <input
                  data-testid="studio-tone-input"
                  value={formState.tone}
                  onChange={(event) =>
                    setFormState((current) => ({ ...current, tone: event.target.value }))
                  }
                />
              </label>
              <div className="studio-form__actions">
                <Button type="submit" disabled={workbench.isBusy} data-testid="studio-create-draft">
                  Create workspace
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={workbench.isBusy || !workspace}
                  onClick={() => void runWorkspace()}
                  data-testid="studio-run"
                >
                  Run draft
                </Button>
              </div>
            </form>
          </Panel>
        </div>

        <div className="studio-workbench__column studio-workbench__column--wide">
          <Panel title="Workspace status" eyebrow="Markdown authority" testId="workspace-surface">
            {workspace ? (
              <div className="studio-manuscript">
                <div className="studio-manuscript__summary">
                  <div>
                    <h2 className="studio-manuscript__title" data-testid="studio-active-title">
                      {workspace.story.title}
                    </h2>
                    <p className="studio-manuscript__copy">{workspace.story.premise}</p>
                  </div>
                  <div className="studio-manuscript__badges" data-testid="publish-verdict">
                    <StatusPill tone={reviewTone(Boolean(review?.export_blocked))}>
                      {review?.export_blocked ? 'export blocked' : 'export allowed'}
                    </StatusPill>
                    <StatusPill tone={currentView === 'workspace' ? 'healthy' : 'running'}>
                      {currentView}
                    </StatusPill>
                  </div>
                </div>

                <div className="studio-memory-grid">
                  <article className="studio-memory-card">
                    <h3>Chapters</h3>
                    <p>{workspace.chapters.length} / {workspace.story.target_chapters}</p>
                  </article>
                  <article className="studio-memory-card">
                    <h3>Review blockers</h3>
                    <p>{review?.blockers.length ?? 0}</p>
                  </article>
                  <article className="studio-memory-card">
                    <h3>Warnings</h3>
                    <p>{review?.warnings.length ?? 0}</p>
                  </article>
                  <article className="studio-memory-card">
                    <h3>Exports</h3>
                    <p>{workspace.exports.length}</p>
                  </article>
                </div>

                <div className="studio-workflow__actions">
                  <Button
                    type="button"
                    onClick={() => void runSingleJob('draft')}
                    disabled={workbench.isBusy}
                    data-testid="studio-draft-chapters"
                  >
                    Draft next chapter
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => void runWorkspace()}
                    disabled={workbench.isBusy}
                    data-testid="studio-run-workspace"
                  >
                    Run target chapters
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => void runSingleJob('review')}
                    disabled={workbench.isBusy || workspace.chapters.length === 0}
                    data-testid="studio-review"
                  >
                    Review
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => void runSingleJob('revise')}
                    disabled={workbench.isBusy || workspace.chapters.length === 0}
                    data-testid="studio-revise"
                  >
                    Revise latest chapter
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => void runSingleJob('export')}
                    disabled={workbench.isBusy || workspace.chapters.length === 0}
                    data-testid="studio-export"
                  >
                    Export
                  </Button>
                </div>

                <h3 className="studio-section-title">Chapter Markdown</h3>
                <ul className="studio-chapter-list" data-testid="studio-chapter-list">
                  {workspace.chapters.length ? (
                    workspace.chapters.map((chapter) => (
                      <li key={chapter.filename} className="studio-chapter-card">
                        <div className="studio-chapter-card__header">
                          <strong>Chapter {chapter.chapter_number}</strong>
                          <span>{chapter.word_count} words</span>
                        </div>
                        <h4>{chapter.filename}</h4>
                        <p>{chapter.summary ?? 'No sidecar summary recorded.'}</p>
                      </li>
                    ))
                  ) : (
                    <li className="studio-empty">Run a draft job to create Markdown chapters.</li>
                  )}
                </ul>

                <div className="studio-notes" data-testid="studio-review-panel">
                  <h3>Review</h3>
                  {review ? (
                    <>
                      <dl className="studio-stats studio-stats--compact">
                        <div>
                          <dt>Blockers</dt>
                          <dd>{review.blockers.length}</dd>
                        </div>
                        <div>
                          <dt>Warnings</dt>
                          <dd>{review.warnings.length}</dd>
                        </div>
                        <div>
                          <dt>Suggestions</dt>
                          <dd>{review.suggestions.length}</dd>
                        </div>
                        <div>
                          <dt>Checked</dt>
                          <dd>{formatDate(review.checked_at)}</dd>
                        </div>
                      </dl>
                      <h4>Blockers</h4>
                      <ul className="studio-issue-list">{issueList(review.blockers)}</ul>
                      <h4>Warnings</h4>
                      <ul className="studio-issue-list">{issueList(review.warnings)}</ul>
                      <h4>Suggestions</h4>
                      <ul className="studio-issue-list">{issueList(review.suggestions)}</ul>
                    </>
                  ) : (
                    <p className="studio-empty">No review report yet.</p>
                  )}
                </div>
              </div>
            ) : (
              <div className="studio-manuscript">
                <p className="studio-empty">Create or select a workspace to begin.</p>
              </div>
            )}
          </Panel>
        </div>

        <div className="studio-workbench__column">
          <Panel title="Run journal" eyebrow="Artifacts" testId="playback-desk">
            <div className="studio-console__state" data-testid="studio-workflow-state">
              <strong>{workbench.isBusy ? 'Working...' : jobLabel(workbench.currentJob)}</strong>
              <StatusPill tone={jobTone(workbench.currentJob)}>
                {workbench.currentJob?.status ?? 'idle'}
              </StatusPill>
            </div>

            {workbench.currentJob ? (
              <div className="studio-notes studio-notes--playback" data-testid="studio-run-playback">
                <h3>Latest job</h3>
                <dl className="studio-stats studio-stats--compact">
                  <div>
                    <dt>Operation</dt>
                    <dd>{workbench.currentJob.operation}</dd>
                  </div>
                  <div>
                    <dt>Status</dt>
                    <dd>{workbench.currentJob.status}</dd>
                  </div>
                  <div>
                    <dt>Created</dt>
                    <dd>{formatDate(workbench.currentJob.created_at)}</dd>
                  </div>
                  <div>
                    <dt>Updated</dt>
                    <dd>{formatDate(workbench.currentJob.updated_at)}</dd>
                  </div>
                </dl>
                {workbench.currentJob.error ? (
                  <p className="form-error">{workbench.currentJob.error}</p>
                ) : null}
                {workbench.currentJob.failure_artifact ? (
                  <p className="studio-muted">
                    Failure evidence: {workbench.currentJob.failure_artifact.relative_path}
                  </p>
                ) : null}
              </div>
            ) : (
              <div className="studio-empty">Run a job to inspect status and results.</div>
            )}

            {workspace?.runs.length ? (
              <div className="studio-notes" data-testid="studio-run-history">
                <h3>Run artifacts</h3>
                <ul>
                  {workspace.runs.slice(0, 6).map((run) => (
                    <li key={run.run_id} className="studio-chapter-card">
                      <div className="studio-chapter-card__header">
                        <strong>{run.run_id}</strong>
                        <span>{run.artifact_count} artifacts</span>
                      </div>
                      <p>
                        {run.last_event
                          ? `${run.last_event.operation} ${run.last_event.status}`
                          : 'No events'}
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {workspace?.exports.length ? (
              <div className="studio-notes" data-testid="studio-export-list">
                <h3>Exports</h3>
                <ul>
                  {workspace.exports.map((item) => (
                    <li key={item.relative_path}>
                      {item.filename} / {item.size} bytes
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </Panel>
        </div>
      </section>
    </main>
  );
}
