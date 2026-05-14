import { useMemo, useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import { Button } from '@/components/Button';
import { Panel } from '@/components/Panel';
import { StatusPill } from '@/components/StatusPill';
import type {
  SessionState,
  StorySurfaceView,
} from '@/app/types/auth';
import type {
  StoryCreateRequest,
  StoryGenre,
  StoryHybridReviewReport,
  StoryReviewIssue,
  StoryRunDetailResponse,
  StoryWorkspace,
} from '@/app/types/story';
import type {
  StoryRunStageExecution,
} from '@/app/types/run';
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

const RELATIONSHIP_DEBT_CODES = new Set([
  'relationship_drift',
  'missing_relationship_state',
  'relationship_ledger_gap',
  'relationship_progression_stall',
]);

const HOOK_DEBT_CODES = new Set([
  'missing_hook_payoff',
  'missing_outline_hook',
  'missing_hook',
  'hook_debt',
  'weak_serial_pull',
]);

interface ComposerState {
  title: string;
  genre: StoryGenre;
  premise: string;
  targetChapters: number;
  targetAudience: string;
  themes: string;
  tone: string;
  publish: boolean;
}

const initialComposerState: ComposerState = {
  title: '',
  genre: 'fantasy',
  premise: '',
  targetChapters: 12,
  targetAudience: '',
  themes: '',
  tone: 'commercial web fiction',
  publish: true,
};

function normalizeView(value: string | null | undefined): StorySurfaceView {
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

function providerLabel(provider: string | null | undefined, model: string | null | undefined) {
  if (!provider && !model) return 'Not recorded';
  if (!provider) return model ?? 'Not recorded';
  return model ? `${provider} / ${model}` : provider;
}

function buildPayload(formState: ComposerState): StoryCreateRequest {
  return {
    title: formState.title.trim(),
    genre: formState.genre,
    premise: formState.premise.trim(),
    target_chapters: formState.targetChapters,
    target_audience: formState.targetAudience.trim() || null,
    themes: parseThemes(formState.themes),
    tone: formState.tone.trim() || 'commercial web fiction',
  };
}

function buildStoryLocation(session: SessionState) {
  const params = new URLSearchParams();
  if (session.lastStoryId) params.set('story', session.lastStoryId);
  if (session.lastRunId) params.set('run', session.lastRunId);
  params.set('view', session.lastView ?? 'workspace');
  const query = params.toString();
  return query ? `/studio?${query}` : '/studio';
}

function chapterNumberFromLocation(location: string | null): number | null {
  if (!location) return null;
  const match = location.match(/chapter-(\d+)/i);
  return match ? Number(match[1]) : null;
}

function debtIssues(review: StoryHybridReviewReport | null, codes: ReadonlySet<string>) {
  return review?.issues.filter((issue) => codes.has(issue.code)) ?? [];
}

function stageTone(stage: StoryRunStageExecution) {
  if (stage.status === 'completed') return 'healthy' as const;
  if (stage.status === 'failed') return 'offline' as const;
  return 'running' as const;
}

function reviewTone(zeroWarning: boolean) {
  return zeroWarning ? 'healthy' : 'degraded';
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
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [formState, setFormState] = useState<ComposerState>(initialComposerState);
  const [rerunPublishes, setRerunPublishes] = useState(false);
  const auth = useAuth();
  const session = auth.session;
  const sessions = auth.sessions ?? [];
  const activeSessionId = auth.activeSessionId ?? null;
  const signOut = auth.signOut;
  const switchSession = auth.switchSession;
  const updateSessionSelection = auth.updateSessionSelection;

  if (!session) return null;

  const preferredStoryId = searchParams.get('story') ?? session.lastStoryId ?? null;
  const preferredRunId = searchParams.get('run') ?? session.lastRunId ?? null;
  const preferredView = normalizeView(searchParams.get('view') ?? session.lastView ?? 'workspace');

  const workbench = useStoryWorkbench({
    authorId: session.workspaceId,
    preferredStoryId,
    preferredRunId,
    onSelectionChange: ({ storyId, runId, view }) => {
      updateSessionSelection({ lastStoryId: storyId, lastRunId: runId, lastView: view });
      const params = new URLSearchParams(searchParams);
      if (storyId) params.set('story', storyId);
      else params.delete('story');
      if (runId) params.set('run', runId);
      else params.delete('run');
      params.set('view', view);
      setSearchParams(params, { replace: true });
    },
  });

  const availableSessions = useMemo(
    () => sessions.filter((entry) => entry.id !== activeSessionId).slice(0, 4),
    [activeSessionId, sessions],
  );
  const review = workbench.workspace?.review ?? workbench.workspace?.hybrid_review ?? workbench.artifact.review;
  const relationshipDebtIssues = debtIssues(review, RELATIONSHIP_DEBT_CODES);
  const hookDebtIssues = debtIssues(review, HOOK_DEBT_CODES);
  const zeroWarning =
    workbench.workspace?.evidence_summary?.zero_warning ??
    ((review?.issues.filter((issue) => issue.severity !== 'info').length ?? 0) === 0);
  const workspaceSummary =
    workbench.workspace?.workspace_context?.summary ??
    session.activeWorkspace?.summary ??
    'Server-validated workspace context with resumable story selection.';
  const rerunTargetChapters =
    workbench.workspace?.workflow.target_chapters ??
    workbench.activeStory?.chapter_count ??
    formState.targetChapters;
  const currentView = workbench.selectedRunDetail ? 'playback' : preferredView;

  const setQuerySelection = (storyId: string | null, runId: string | null, view: StorySurfaceView) => {
    const params = new URLSearchParams(searchParams);
    if (storyId) params.set('story', storyId);
    else params.delete('story');
    if (runId) params.set('run', runId);
    else params.delete('run');
    params.set('view', view);
    setSearchParams(params, { replace: true });
  };

  const createDraft = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      const story = await workbench.createStory(buildPayload(formState));
      setQuerySelection(story.id, null, 'workspace');
    } catch {}
  };

  const runInitialPipeline = async () => {
    try {
      const result = await workbench.runPipeline({
        ...buildPayload(formState),
        publish: formState.publish,
      });
      setQuerySelection(result.story.id, null, 'workspace');
    } catch {}
  };

  const rerunCurrentPipeline = async () => {
    try {
      const result = await workbench.runStoryPipeline({
        publish: rerunPublishes,
        targetChapters: rerunTargetChapters,
      });
      setQuerySelection(workbench.activeStoryId, result.run.run_id, 'playback');
    } catch {}
  };

  const switchToSavedSession = async (sessionId: string) => {
    try {
      const nextSession = await switchSession(sessionId);
      navigate(buildStoryLocation(nextSession));
    } catch {}
  };

  const leaveCurrentSession = () => {
    signOut();
    navigate('/');
  };

  const handleGuidedAction = async () => {
    const action = workbench.workspace?.recommended_next_action?.action;
    if (!action) return;
    switch (action) {
      case 'generate_blueprint':
        await workbench.generateBlueprint();
        break;
      case 'generate_outline':
        await workbench.generateOutline();
        break;
      case 'draft':
        await workbench.draftStory();
        break;
      case 'review':
        await workbench.reviewStory();
        break;
      case 'revise':
        await workbench.reviseStory();
        break;
      case 'export':
        await workbench.exportStory();
        break;
      case 'publish':
        await workbench.publishStory();
        break;
      case 'view_playback':
        if (workbench.runSummaries[0]) {
          await workbench.selectRun(workbench.runSummaries[0].run_id);
        }
        break;
      default:
        break;
    }
  };

  const openStory = async (storyId: string) => {
    try {
      await workbench.selectStory(storyId);
    } catch {}
  };

  const toggleRun = async (runId: string) => {
    try {
      await workbench.selectRun(workbench.selectedRunId === runId ? null : runId);
    } catch {}
  };

  const playbackWorkspace = workbench.selectedRunDetail?.latest_snapshot?.workspace ?? null;
  const playbackReview =
    playbackWorkspace?.review ?? playbackWorkspace?.hybrid_review ?? null;

  return (
    <main className="studio-workbench" data-testid="studio-workbench-page">
      <header className="studio-workbench__hero">
        <div className="studio-workbench__hero-copy">
          <p className="studio-workbench__eyebrow">Novel Engine / Guided Author Shell</p>
          <h1 className="studio-workbench__title">
            {workbench.activeStory ? workbench.activeStory.title : 'Create or resume a manuscript'}
          </h1>
          <p className="studio-workbench__summary">
            Session context, manuscript selection, and playback selection are now addressable.
            Mutable workspace and immutable playback stay visually and semantically separate.
          </p>
        </div>

        <div className="studio-workbench__hero-meta">
          <StatusPill tone={session.kind === 'guest' ? 'idle' : 'running'}>
            {session.kind === 'guest' ? 'guest session' : 'signed in'}
          </StatusPill>
          <span data-testid="zero-warning-badge">
            <StatusPill tone={reviewTone(zeroWarning)}>
              {zeroWarning ? 'zero warning' : 'warnings open'}
            </StatusPill>
          </span>
          <span className="studio-workbench__workspace" data-testid="workspace-badge">
            {session.workspaceId}
          </span>
        </div>
      </header>

      {workbench.error ? <p className="form-error">{workbench.error}</p> : null}

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
            title="Library"
            eyebrow="Manuscripts"
            actions={
              <Button variant="ghost" onClick={() => void workbench.refreshLibrary()} disabled={workbench.isLoading}>
                {workbench.isLoading ? 'Refreshing...' : 'Refresh library'}
              </Button>
            }
            testId="studio-library-panel"
          >
            <div className="studio-library-summary" data-testid="studio-library-summary">
              <strong>{workbench.stories.length} manuscript(s)</strong>
              <span>
                {workbench.activeStory
                  ? `Viewing ${workbench.activeStory.title}`
                  : 'Select a manuscript or create a new one.'}
              </span>
            </div>
            <div data-testid="library-list">
              <ul className="studio-list" data-testid="studio-list">
                {workbench.stories.length === 0 ? (
                  <li className="studio-empty">No manuscripts yet. Create the first draft below.</li>
                ) : (
                  workbench.stories.map((story) => (
                    <li
                      key={story.id}
                      className={`studio-card${story.id === workbench.activeStoryId ? ' studio-card--active' : ''}`}
                    >
                      <button
                        className="studio-card__button"
                        type="button"
                        onClick={() => void openStory(story.id)}
                        data-testid={`studio-item-${story.id}`}
                      >
                        <div className="studio-card__header">
                          <strong>{story.title}</strong>
                          <span>{story.status}</span>
                        </div>
                        <p className="studio-card__meta">
                          {story.genre} / {story.chapter_count} chapters / updated {formatDate(story.updated_at)}
                        </p>
                      </button>
                    </li>
                  ))
                )}
              </ul>
            </div>
          </Panel>

          <Panel title="New manuscript" eyebrow="Create" testId="studio-create-panel">
            <form className="studio-form" onSubmit={createDraft} data-testid="studio-create-form">
              <label className="field">
                <span>Title</span>
                <input data-testid="studio-title-input" value={formState.title} onChange={(event) => setFormState((current) => ({ ...current, title: event.target.value }))} required />
              </label>
              <label className="field">
                <span>Genre</span>
                <select data-testid="studio-genre-select" value={formState.genre} onChange={(event) => setFormState((current) => ({ ...current, genre: event.target.value as StoryGenre }))}>
                  {STORY_GENRES.map((genre) => <option key={genre} value={genre}>{genre}</option>)}
                </select>
              </label>
              <label className="field">
                <span>Premise</span>
                <textarea data-testid="studio-premise-input" value={formState.premise} onChange={(event) => setFormState((current) => ({ ...current, premise: event.target.value }))} rows={5} required />
              </label>
              <div className="studio-form__grid">
                <label className="field">
                  <span>Target chapters</span>
                  <input data-testid="studio-target-chapters-input" type="number" min={1} max={120} value={formState.targetChapters} onChange={(event) => setFormState((current) => ({ ...current, targetChapters: Number(event.target.value) }))} required />
                </label>
                <label className="field">
                  <span>Audience</span>
                  <input data-testid="studio-audience-input" value={formState.targetAudience} onChange={(event) => setFormState((current) => ({ ...current, targetAudience: event.target.value }))} />
                </label>
              </div>
              <label className="field">
                <span>Themes</span>
                <input data-testid="studio-themes-input" value={formState.themes} onChange={(event) => setFormState((current) => ({ ...current, themes: event.target.value }))} />
              </label>
              <label className="field">
                <span>Tone</span>
                <input data-testid="studio-tone-input" value={formState.tone} onChange={(event) => setFormState((current) => ({ ...current, tone: event.target.value }))} />
              </label>
              <label className="studio-toggle">
                <input data-testid="studio-publish-toggle" type="checkbox" checked={formState.publish} onChange={(event) => setFormState((current) => ({ ...current, publish: event.target.checked }))} />
                <span>Publish after the initial full pipeline</span>
              </label>
              <div className="studio-form__actions">
                <Button type="submit" disabled={workbench.isBusy} data-testid="studio-create-draft">Create draft</Button>
                <Button type="button" variant="secondary" disabled={workbench.isBusy} onClick={() => void runInitialPipeline()} data-testid="studio-run-pipeline">Run full pipeline</Button>
              </div>
            </form>
          </Panel>
        </div>

        <div className="studio-workbench__column studio-workbench__column--wide">
          <Panel title="Guided workspace" eyebrow="Mutable surface" testId="workspace-surface">
            {workbench.activeStory && workbench.workspace ? (
              <div className="studio-manuscript">
                <div className="studio-manuscript__summary">
                  <div>
                    <h2 className="studio-manuscript__title" data-testid="studio-active-title">
                      {workbench.activeStory.title}
                    </h2>
                    <p className="studio-manuscript__copy">
                      {workbench.workspace.workflow.premise || 'Premise pending.'}
                    </p>
                  </div>
                  <div className="studio-manuscript__badges" data-testid="publish-verdict">
                    <StatusPill tone={reviewTone(zeroWarning)}>
                      {zeroWarning ? 'zero warning ready' : 'review debt open'}
                    </StatusPill>
                    <StatusPill tone={reviewTone(currentView === 'workspace')}>
                      {currentView}
                    </StatusPill>
                  </div>
                </div>

                <div className="studio-memory-grid">
                  <article className="studio-memory-card">
                    <h3>Recommended next action</h3>
                    <p>{workbench.workspace.recommended_next_action?.label ?? 'Create the next manuscript step.'}</p>
                    <p>{workbench.workspace.recommended_next_action?.reason ?? 'No guided action available yet.'}</p>
                    <Button type="button" onClick={() => void handleGuidedAction()} disabled={!workbench.workspace.recommended_next_action || workbench.isBusy} data-testid="guided-next-action">
                      {workbench.workspace.recommended_next_action?.label ?? 'No guided action'}
                    </Button>
                  </article>
                  <article className="studio-memory-card">
                    <h3>Target chapters</h3>
                    <p>{workbench.workspace.workflow.target_chapters}</p>
                  </article>
                  <article className="studio-memory-card">
                    <h3>Drafted chapters</h3>
                    <p>{workbench.activeStory.chapter_count}</p>
                  </article>
                  <article className="studio-memory-card">
                    <h3>Artifacts</h3>
                    <p>{workbench.workspace.artifact_history.length}</p>
                  </article>
                </div>

                <div className="studio-notes" data-testid="studio-review-panel">
                  <h3>Quality summary</h3>
                  <dl className="studio-stats studio-stats--compact">
                    <div>
                      <dt>Review score</dt>
                      <dd data-testid="studio-review-score">{review?.quality_score ?? 0}</dd>
                    </div>
                    <div>
                      <dt>Warnings</dt>
                      <dd>{workbench.workspace.evidence_summary?.warning_count ?? 0}</dd>
                    </div>
                    <div>
                      <dt>Blockers</dt>
                      <dd>{workbench.workspace.evidence_summary?.blocker_count ?? 0}</dd>
                    </div>
                    <div>
                      <dt>Publish gate</dt>
                      <dd>{review?.publish_gate_passed ? 'pass' : 'blocked'}</dd>
                    </div>
                  </dl>
                </div>

                <div className="studio-workflow__actions">
                  <Button type="button" onClick={() => void workbench.generateBlueprint()} disabled={workbench.isBusy} data-testid="studio-generate-blueprint">Generate blueprint</Button>
                  <Button type="button" variant="secondary" onClick={() => void workbench.generateOutline()} disabled={workbench.isBusy || !workbench.workspace.blueprint} data-testid="studio-generate-outline">Generate outline</Button>
                  <Button type="button" variant="secondary" onClick={() => void workbench.draftStory()} disabled={workbench.isBusy || !workbench.workspace.outline} data-testid="studio-draft-chapters">Draft chapters</Button>
                  <Button type="button" variant="secondary" onClick={() => void workbench.reviewStory()} disabled={workbench.isBusy || workbench.activeStory.chapter_count === 0} data-testid="studio-review">Review</Button>
                  <Button type="button" variant="secondary" onClick={() => void workbench.reviseStory()} disabled={workbench.isBusy || !review} data-testid="studio-revise">Revise</Button>
                </div>

                <details className="studio-notes" open={currentView === 'workspace'}>
                  <summary>Advanced diagnostics</summary>
                  <dl className="studio-stats studio-stats--compact">
                    <div>
                      <dt>Blueprint source</dt>
                      <dd>{workbench.workspace.blueprint ? providerLabel(workbench.workspace.blueprint.provider, workbench.workspace.blueprint.model) : 'Not generated'}</dd>
                    </div>
                    <div>
                      <dt>Outline source</dt>
                      <dd>{workbench.workspace.outline ? providerLabel(workbench.workspace.outline.provider, workbench.workspace.outline.model) : 'Not generated'}</dd>
                    </div>
                    <div>
                      <dt>Review source</dt>
                      <dd>{review ? providerLabel(review.source_provider, review.source_model) : 'Not reviewed'}</dd>
                    </div>
                  </dl>

                  <div className="studio-memory-grid">
                    <article className="studio-memory-card"><h3>Relationship debt</h3><p data-testid="studio-relationship-debt-count">{relationshipDebtIssues.length}</p></article>
                    <article className="studio-memory-card"><h3>Hook debt</h3><p data-testid="studio-hook-debt-count">{hookDebtIssues.length}</p></article>
                  </div>

                  <ul className="studio-issue-list" data-testid="studio-debt-issue-list">
                    {[...relationshipDebtIssues, ...hookDebtIssues].length === 0 ? (
                      <li className="studio-empty">No highlighted relationship or hook debt.</li>
                    ) : (
                      [...relationshipDebtIssues, ...hookDebtIssues].map((issue, index) => (
                        <li key={`${issue.code}-${issue.location ?? 'story'}-${index}`} className="studio-chapter-card">
                          <div className="studio-chapter-card__header">
                            <strong>{issue.code}</strong>
                            <span>{issue.severity}</span>
                          </div>
                          <p>{issue.message}</p>
                        </li>
                      ))
                    )}
                  </ul>
                </details>

                <h3 className="studio-section-title">Chapter map</h3>
                <ul className="studio-chapter-list" data-testid="studio-chapter-list">
                  {workbench.activeStory.chapters.length ? (
                    workbench.activeStory.chapters.map((chapter) => {
                      const chapterIssues = review?.issues.filter((issue) => chapterNumberFromLocation(issue.location) === chapter.chapter_number) ?? [];
                      const hasRelationshipDebt = chapterIssues.some((issue) => RELATIONSHIP_DEBT_CODES.has(issue.code));
                      const hasHookDebt = chapterIssues.some((issue) => HOOK_DEBT_CODES.has(issue.code));
                      return (
                        <li key={chapter.id} className="studio-chapter-card">
                          <div className="studio-chapter-card__header">
                            <strong>Chapter {chapter.chapter_number}</strong>
                            <span>{chapter.scenes.length} scenes</span>
                          </div>
                          <h4>{chapter.title}</h4>
                          <p>{chapter.summary ?? 'No summary yet.'}</p>
                          {hasRelationshipDebt || hasHookDebt ? (
                            <div className="studio-tag-row" data-testid={`studio-chapter-debt-${chapter.chapter_number}`}>
                              {hasRelationshipDebt ? <span className="studio-tag">relationship debt</span> : null}
                              {hasHookDebt ? <span className="studio-tag">hook debt</span> : null}
                            </div>
                          ) : null}
                        </li>
                      );
                    })
                  ) : (
                    <li className="studio-empty">Draft chapters to populate the manuscript map.</li>
                  )}
                </ul>
              </div>
            ) : (
              <div className="studio-manuscript">
                <div className="studio-memory-grid">
                  <article className="studio-memory-card">
                    <h3>Recommended next action</h3>
                    <p>Start with a new manuscript in the create rail, then the workspace will advance one stage at a time.</p>
                    <Button type="button" disabled data-testid="guided-next-action">
                      Create a manuscript in the left rail
                    </Button>
                  </article>
                </div>
                <p className="studio-empty">Select a manuscript from the library or create a new one.</p>
              </div>
            )}
          </Panel>
        </div>

        <div className="studio-workbench__column">
          <Panel title="Playback desk" eyebrow="Immutable surface" testId="playback-desk">
            <div className="studio-notes" data-testid="studio-run-provenance">
              <h3>Run provenance</h3>
              <p>The playback desk shows immutable run evidence, stage snapshots, and publish verdicts.</p>
              <dl className="studio-stats studio-stats--compact">
                <div><dt>Selected run</dt><dd>{workbench.selectedRunDetail?.run.run_id ?? 'None selected'}</dd></div>
                <div><dt>Playback source</dt><dd>{workbench.selectedRunDetail?.provenance ? providerLabel(workbench.selectedRunDetail.provenance.source_providers[0], workbench.selectedRunDetail.provenance.source_models[0]) : 'No playback selected'}</dd></div>
                <div><dt>Snapshot</dt><dd>{formatDate(workbench.selectedRunDetail?.provenance?.snapshot_captured_at ?? null)}</dd></div>
                <div><dt>Mutable run</dt><dd>{workbench.currentRun?.run_id ?? workbench.workspace?.run?.run_id ?? 'No active run'}</dd></div>
              </dl>
            </div>

            <label className="studio-toggle studio-toggle--panel">
              <input data-testid="studio-current-publish-toggle" type="checkbox" checked={rerunPublishes} onChange={(event) => setRerunPublishes(event.target.checked)} disabled={!workbench.activeStory || workbench.isBusy} />
              <span>Publish when rerunning the current manuscript ({rerunTargetChapters} target chapters)</span>
            </label>

            <div className="studio-workflow__actions">
              <Button type="button" variant="secondary" onClick={() => void rerunCurrentPipeline()} disabled={!workbench.activeStory || workbench.isBusy} data-testid="studio-run-current-pipeline">{rerunPublishes ? 'Run current pipeline and publish' : 'Run current pipeline'}</Button>
              <Button type="button" variant="secondary" onClick={() => void workbench.exportStory()} disabled={!workbench.activeStory || workbench.isBusy} data-testid="studio-export">Export</Button>
              <Button type="button" variant="secondary" onClick={() => void workbench.publishStory()} disabled={!workbench.activeStory || workbench.isBusy || !zeroWarning} data-testid="studio-publish">Publish</Button>
            </div>

            <div className="studio-console__state" data-testid="studio-workflow-state">
              <strong>{workbench.isBusy ? 'Working...' : workbench.artifact.lastAction ?? 'Waiting for an action'}</strong>
              <span>{workbench.stories.length} manuscripts tracked</span>
            </div>

            {workbench.runSummaries.length ? (
              <div className="studio-notes" data-testid="studio-run-history">
                <h3>Run history</h3>
                <ul>
                  {workbench.runSummaries.slice(-6).reverse().map((run) => (
                    <li key={run.run_id}>
                      <button type="button" className="studio-card__button" onClick={() => void toggleRun(run.run_id)} data-testid={`studio-run-item-${run.run_id}`}>
                        <strong>{workbench.selectedRunId === run.run_id ? 'Viewing' : 'Open'} {run.mode}</strong>
                        <span>{run.status} / {run.stages.length} stages / {formatDate(run.completed_at ?? run.started_at)}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {workbench.selectedRunDetail ? (
              <div className="studio-notes studio-notes--playback" data-testid="studio-run-playback">
                <h3>Run playback</h3>
                <p>{workbench.selectedRunDetail.run.mode} / {workbench.selectedRunDetail.run.status} / snapshot {formatDate(workbench.selectedRunDetail.latest_snapshot?.captured_at ?? null)}</p>
                <dl className="studio-stats" data-testid="studio-run-playback-stats">
                  <div><dt>Artifacts</dt><dd>{workbench.selectedRunDetail.artifacts.length}</dd></div>
                  <div><dt>Events</dt><dd>{workbench.selectedRunDetail.events.length}</dd></div>
                  <div><dt>Snapshots</dt><dd>{workbench.selectedRunDetail.stage_snapshots.length}</dd></div>
                  <div><dt>Quality</dt><dd>{playbackReview?.quality_score ?? 0}</dd></div>
                  <div><dt>Reader pull</dt><dd>{playbackReview?.semantic_review?.metrics.reader_pull_score ?? 0}</dd></div>
                </dl>
                <div className="studio-tag-row">
                  <span className="studio-tag" data-testid="studio-playback-structural-gate">Structural gate: {playbackReview?.structural_gate_passed ? 'pass' : 'blocked'}</span>
                  <span className="studio-tag" data-testid="studio-playback-semantic-gate">Semantic gate: {playbackReview?.semantic_gate_passed ? 'pass' : 'blocked'}</span>
                  <span className="studio-tag" data-testid="studio-playback-publish-gate">Publish gate: {playbackReview?.publish_gate_passed ? 'pass' : 'blocked'}</span>
                </div>

                <ul className="studio-issue-list" data-testid="playback-stage-timeline">
                  {workbench.selectedRunDetail.run.stages.map((stage) => (
                    <li key={`${stage.name}-${stage.started_at}`} className="studio-chapter-card">
                      <div className="studio-chapter-card__header">
                        <strong>{stage.name}</strong>
                        <StatusPill tone={stageTone(stage)}>{stage.status}</StatusPill>
                      </div>
                      <p>{stage.failure_code ? `${stage.name}: ${stage.failure_code}` : `${stage.name}: ${stage.status}`}</p>
                    </li>
                  ))}
                </ul>

                {workbench.selectedRunDetail.failure_message || workbench.selectedRunDetail.run.status === 'failed' ? (
                  <div className="studio-notes" data-testid="studio-run-failure">
                    <h3>Run failure</h3>
                    <p>Failed stage: {workbench.selectedRunDetail.failed_stage ?? 'unknown'}{workbench.selectedRunDetail.failure_code ? ` / ${workbench.selectedRunDetail.failure_code}` : ''}</p>
                    <p>{workbench.selectedRunDetail.failure_message ?? 'No failure message recorded.'}</p>
                    <p>Manuscript preserved: {workbench.selectedRunDetail.manuscript_preserved === false ? 'no' : 'yes'}</p>
                    <p>Debug artifacts: {workbench.selectedRunDetail.failure_artifacts?.length ?? 0}</p>
                    {workbench.selectedRunDetail.failure_artifacts?.length ? (
                      <ul>
                        {workbench.selectedRunDetail.failure_artifacts.slice(-3).map((artifact) => (
                          <li key={artifact.artifact_id}>{artifact.kind} v{artifact.version} / {artifact.source_provider}</li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="studio-empty">Select a run from the history to inspect immutable evidence.</div>
            )}
          </Panel>
        </div>
      </section>
    </main>
  );
}
