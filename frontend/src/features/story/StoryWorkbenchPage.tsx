import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

import { Button } from '@/components/Button';
import { Panel } from '@/components/Panel';
import { StatusPill } from '@/components/StatusPill';
import type {
  StoryReviewIssue,
  StoryCreateRequest,
  StoryGenre,
  StoryPipelineRequest,
  StoryRunStageExecution,
  StoryWorkspace,
} from '@/app/types';
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

const RELATIONSHIP_DEBT_CODES = new Set([
  'relationship_drift',
  'missing_relationship_state',
  'relationship_ledger_gap',
]);

const HOOK_DEBT_CODES = new Set([
  'missing_hook_payoff',
  'missing_outline_hook',
  'missing_hook',
  'hook_debt',
]);

function storyTone(status: string | null | undefined): 'draft' | 'running' | 'completed' {
  if (status === 'active') {
    return 'running';
  }

  if (status === 'completed') {
    return 'completed';
  }

  return 'draft';
}

function reviewTone(readyForPublish: boolean | undefined): 'healthy' | 'degraded' {
  return readyForPublish ? 'healthy' : 'degraded';
}

function stageTone(
  isReady: boolean,
  isLocked: boolean,
): 'healthy' | 'degraded' | 'idle' {
  if (isLocked) {
    return 'idle';
  }

  return isReady ? 'healthy' : 'degraded';
}

function formatDate(value: string | undefined | null): string {
  if (!value) {
    return 'Unknown';
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function parseThemes(rawThemes: string): string[] {
  return rawThemes
    .split(',')
    .map((theme) => theme.trim())
    .filter(Boolean);
}

function buildPayload(
  authorId: string,
  formState: ComposerState,
): StoryCreateRequest {
  return {
    title: formState.title.trim(),
    genre: formState.genre,
    premise: formState.premise.trim(),
    target_chapters: formState.targetChapters,
    target_audience: formState.targetAudience.trim() || null,
    themes: parseThemes(formState.themes),
    tone: formState.tone.trim() || 'commercial web fiction',
    author_id: authorId,
  };
}

function storyStatusLabel(status: string | null | undefined): string {
  if (!status) {
    return 'draft';
  }

  return status;
}

function unresolvedHooks(workspace: StoryWorkspace | null) {
  return workspace?.memory.hook_ledger.filter((entry) => !entry.surfaced) ?? [];
}

function unresolvedPromises(workspace: StoryWorkspace | null) {
  return (
    workspace?.memory.promise_ledger.filter(
      (entry) => entry.status !== 'paid_off' && Boolean(entry.promise),
    ) ?? []
  );
}

function overduePayoffs(workspace: StoryWorkspace | null) {
  const chapterCount = workspace?.story.chapter_count ?? 0;
  return unresolvedPromises(workspace).filter(
    (entry) => entry.due_by_chapter !== null && entry.due_by_chapter <= chapterCount,
  );
}

function semanticBlockers(workspace: StoryWorkspace | null) {
  return (
    workspace?.semantic_review?.issues.filter((issue) => issue.severity === 'blocker') ??
    []
  );
}

function strandGapCount(workspace: StoryWorkspace | null) {
  if (!workspace) {
    return 0;
  }

  const thresholds = {
    quest: 5,
    fire: 10,
    constellation: 15,
  } as const;
  const chapterCount = workspace.story.chapter_count;
  const latestByStrand = new Map<string, number>();

  workspace.memory.strand_ledger.forEach((entry) => {
    if (!entry.strand) {
      return;
    }
    latestByStrand.set(entry.strand, entry.chapter_number);
  });

  return Object.entries(thresholds).filter(([strand, limit]) => {
    const latest = latestByStrand.get(strand) ?? 0;
    return chapterCount - latest > limit;
  }).length;
}

function blockingIssues(workspace: StoryWorkspace | null) {
  return workspace?.review?.issues.filter((issue) => issue.severity === 'blocker') ?? [];
}

function debtIssues(
  workspace: StoryWorkspace | null,
  codes: ReadonlySet<string>,
): StoryReviewIssue[] {
  return workspace?.review?.issues.filter((issue) => codes.has(issue.code)) ?? [];
}

function chapterNumberFromLocation(location: string | null): number | null {
  if (!location) {
    return null;
  }

  const match = location.match(/chapter-(\d+)/i);
  if (!match) {
    return null;
  }

  const chapterNumber = Number(match[1]);
  return Number.isFinite(chapterNumber) ? chapterNumber : null;
}

function chapterNumbersFromDetails(issue: StoryReviewIssue): number[] {
  const chapters = issue.details.chapters;
  if (!Array.isArray(chapters)) {
    return [];
  }

  return chapters
    .map((chapter) => Number(chapter))
    .filter((chapter) => Number.isFinite(chapter));
}

function issueTargetsChapter(issue: StoryReviewIssue, chapterNumber: number): boolean {
  if (chapterNumberFromLocation(issue.location) === chapterNumber) {
    return true;
  }

  return chapterNumbersFromDetails(issue).includes(chapterNumber);
}

function stageStatusLabel(stage: StoryRunStageExecution): string {
  if (stage.failure_code) {
    return `${stage.name}: ${stage.failure_code}`;
  }

  return `${stage.name}: ${stage.status}`;
}

function providerLabel(provider: string | null | undefined, model: string | null | undefined) {
  if (!provider && !model) {
    return 'Not recorded';
  }

  if (!provider) {
    return model ?? 'Not recorded';
  }

  return model ? `${provider} / ${model}` : provider;
}

export function StoryWorkbenchPage() {
  const { session, signOut } = useAuth();
  const [formState, setFormState] = useState<ComposerState>(initialComposerState);
  const [rerunPublishes, setRerunPublishes] = useState(false);

  if (!session) {
    return null;
  }

  const {
    stories,
    activeStoryId,
    activeStory,
    workspace,
    currentRun,
    runSummaries,
    selectedRunId,
    selectedRunDetail,
    artifact,
    isLoading,
    isBusy,
    error,
    refreshLibrary,
    selectStory,
    selectRun,
    createStory,
    generateBlueprint,
    generateOutline,
    draftStory,
    reviewStory,
    reviseStory,
    exportStory,
    publishStory,
    runPipeline,
    runStoryPipeline,
  } = useStoryWorkbench(session.workspaceId);

  const workflow = workspace?.workflow ?? null;
  const memory = workspace?.memory ?? null;
  const review = workspace?.review ?? artifact.review;
  const structuralReview = workspace?.structural_review ?? review?.structural_review ?? null;
  const semanticReview = workspace?.semantic_review ?? review?.semantic_review ?? null;
  const structuralGatePassed =
    review?.structural_gate_passed ?? structuralReview?.ready_for_publish ?? false;
  const semanticGatePassed =
    review?.semantic_gate_passed ?? semanticReview?.ready_for_publish ?? false;
  const publishGatePassed = review?.publish_gate_passed ?? review?.ready_for_publish ?? false;
  const runState = currentRun ?? workspace?.run ?? artifact.run;
  const exportPayload = workspace?.export ?? artifact.exportPayload;
  const runHistory = runSummaries;
  const runEvents = workspace?.run_events ?? [];
  const artifactHistory = workspace?.artifact_history ?? [];
  const latestRunEvent = runEvents.length > 0 ? runEvents[runEvents.length - 1] : null;
  const unresolvedHookEntries = unresolvedHooks(workspace);
  const unresolvedPromiseEntries = unresolvedPromises(workspace);
  const overduePayoffEntries = overduePayoffs(workspace);
  const semanticBlockingIssues = semanticBlockers(workspace);
  const activeStrandGaps = strandGapCount(workspace);
  const blockingReviewIssues = blockingIssues(workspace);
  const relationshipDebtIssues = debtIssues(workspace, RELATIONSHIP_DEBT_CODES);
  const hookDebtIssues = debtIssues(workspace, HOOK_DEBT_CODES);
  const highlightedDebtIssues = (review?.issues ?? []).filter(
    (issue) =>
      RELATIONSHIP_DEBT_CODES.has(issue.code) || HOOK_DEBT_CODES.has(issue.code),
  );
  const playbackWorkspace = selectedRunDetail?.latest_snapshot?.workspace ?? null;
  const playbackReview = playbackWorkspace?.review ?? null;
  const playbackStructuralReview =
    playbackWorkspace?.structural_review ?? playbackReview?.structural_review ?? null;
  const playbackSemanticReview =
    playbackWorkspace?.semantic_review ?? playbackReview?.semantic_review ?? null;
  const playbackStructuralGatePassed =
    playbackReview?.structural_gate_passed ?? playbackStructuralReview?.ready_for_publish ?? false;
  const playbackSemanticGatePassed =
    playbackReview?.semantic_gate_passed ?? playbackSemanticReview?.ready_for_publish ?? false;
  const playbackPublishGatePassed =
    playbackReview?.publish_gate_passed ?? playbackReview?.ready_for_publish ?? false;
  const playbackFailureSnapshot = selectedRunDetail?.failure_snapshot ?? null;
  const playbackFailureArtifacts = selectedRunDetail?.failure_artifacts ?? [];
  const playbackFailureMessage =
    selectedRunDetail?.failure_message ?? playbackFailureSnapshot?.failure_message ?? null;
  const playbackFailedStage =
    selectedRunDetail?.failed_stage ?? playbackFailureSnapshot?.failed_stage ?? null;
  const playbackManuscriptPreserved =
    selectedRunDetail?.manuscript_preserved ??
    playbackFailureSnapshot?.failure_details?.manuscript_preserved ??
    null;
  const playbackRunEvent =
    selectedRunDetail && selectedRunDetail.events.length > 0
      ? selectedRunDetail.events[selectedRunDetail.events.length - 1]
      : null;
  const playbackRelationshipDebtIssues = debtIssues(
    playbackWorkspace,
    RELATIONSHIP_DEBT_CODES,
  );
  const playbackHookDebtIssues = debtIssues(playbackWorkspace, HOOK_DEBT_CODES);
  const playbackBlockingIssues = blockingIssues(playbackWorkspace);
  const playbackUnresolvedHooks = unresolvedHooks(playbackWorkspace);
  const playbackUnresolvedPromises = unresolvedPromises(playbackWorkspace);
  const playbackOverduePayoffs = overduePayoffs(playbackWorkspace);
  const playbackSemanticBlockingIssues = semanticBlockers(playbackWorkspace);
  const playbackStrandGaps = strandGapCount(playbackWorkspace);

  const createDraft = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    try {
      await createStory(buildPayload(session.workspaceId, formState));
    } catch {
      // The hook owns error presentation.
    }
  };

  const launchPipeline = async () => {
    const payload: StoryPipelineRequest = {
      ...buildPayload(session.workspaceId, formState),
      publish: formState.publish,
    };

    try {
      await runPipeline(payload);
    } catch {
      // The hook owns error presentation.
    }
  };

  const handleStorySelect = async (storyId: string) => {
    try {
      await selectStory(storyId);
    } catch {
      // The hook owns error presentation.
    }
  };

  const launchActivePipeline = async () => {
    try {
      await runStoryPipeline({
        publish: rerunPublishes,
        targetChapters: rerunTargetChapters,
      });
    } catch {
      // The hook owns error presentation.
    }
  };

  const selectedCharacterCount = memory?.active_characters?.length ?? 0;
  const chapterSummaryCount = memory?.chapter_summaries?.length ?? 0;
  const targetChapters = workflow?.target_chapters ?? formState.targetChapters;
  const rerunTargetChapters =
    workflow?.target_chapters ?? activeStory?.chapter_count ?? formState.targetChapters;
  const canOutline = Boolean(workspace?.blueprint);
  const canDraft = Boolean(workspace?.outline);
  const canReview = Boolean(activeStory && activeStory.chapter_count > 0);
  const canPublish = Boolean(publishGatePassed);
  const sessionTitle =
    session.kind === 'user'
      ? session.user?.name ?? 'Signed in author'
      : 'Guest author workspace';
  const sessionSummary =
    session.kind === 'user'
      ? session.user?.email ?? 'Profile email missing'
      : 'Guest sessions are disposable and useful for zero-state flow validation.';
  const activeRunLabel = runState ? `${runState.mode} / ${runState.status}` : 'No active run';
  const blueprintSource = workspace?.blueprint
    ? providerLabel(workspace.blueprint.provider, workspace.blueprint.model)
    : 'Not generated';
  const outlineSource = workspace?.outline
    ? providerLabel(workspace.outline.provider, workspace.outline.model)
    : 'Not generated';
  const semanticSource = semanticReview
    ? providerLabel(semanticReview.source_provider, semanticReview.source_model)
    : 'Not reviewed';
  const selectedPlaybackSource = playbackReview
    ? providerLabel(playbackReview.source_provider, playbackReview.source_model)
    : 'No playback selected';

  return (
    <main className="story-workbench" data-testid="story-workbench-page">
      <header className="story-workbench__hero" data-testid="story-workbench-hero">
        <div className="story-workbench__hero-copy">
          <p className="story-workbench__eyebrow">Novel Engine / Story Workshop</p>
          <h1 className="story-workbench__title">
            {activeStory ? activeStory.title : 'Compose a living manuscript'}
          </h1>
          <p className="story-workbench__summary">
            {activeStory
              ? `当前稿件已完成 ${activeStory.chapter_count}/${targetChapters} 章。稿件库、mutable workspace 和 immutable run playback 现在分层展示，避免用户在当前稿件和历史 run 之间迷路。`
              : '从入口页进入后，先建立稿件，再在同一工作台里管理 library、当前稿件状态和 run playback。全自动 pipeline 是快捷入口，但不再复用别的面板状态。'}
          </p>
        </div>

        <div className="story-workbench__hero-meta">
          <StatusPill tone={session.kind === 'guest' ? 'idle' : 'running'}>
            {session.kind === 'guest' ? 'guest session' : 'signed in'}
          </StatusPill>
          <StatusPill tone={storyTone(activeStory?.status)}>
            {storyStatusLabel(activeStory?.status)}
          </StatusPill>
          <StatusPill tone={reviewTone(publishGatePassed)}>
            {publishGatePassed ? 'publish ready' : 'review pending'}
          </StatusPill>
          <span className="story-workbench__workspace" data-testid="workspace-badge">
            {session.workspaceId}
          </span>
        </div>
      </header>

      {error ? <p className="form-error">{error}</p> : null}

      <section className="story-workbench__layout">
        <div className="story-workbench__column">
          <Panel title="Session / Entry" eyebrow="Surface 1" testId="story-session-panel">
            <div className="story-session-card" data-testid="story-session-summary">
              <StatusPill tone={session.kind === 'guest' ? 'idle' : 'running'}>
                {session.kind === 'guest' ? 'guest session' : 'signed in'}
              </StatusPill>
              <h3>{sessionTitle}</h3>
              <p>{sessionSummary}</p>
              <dl className="story-stats story-stats--compact">
                <div>
                  <dt>Workspace</dt>
                  <dd>{session.workspaceId}</dd>
                </div>
                <div>
                  <dt>Active story</dt>
                  <dd>{activeStory?.title ?? 'No manuscript selected'}</dd>
                </div>
              </dl>
            </div>

            <div className="story-workflow__actions">
              <Link
                className="button button--secondary"
                to="/"
                data-testid="story-back-to-landing"
              >
                Back to landing
              </Link>
              <Button variant="ghost" onClick={signOut}>
                Sign out
              </Button>
            </div>
          </Panel>

          <Panel
            title="Create manuscript"
            eyebrow="New project"
            testId="story-create-panel"
          >
            <form className="story-form" onSubmit={createDraft} data-testid="story-create-form">
              <label className="field">
                <span>Title</span>
                <input
                  data-testid="story-title-input"
                  value={formState.title}
                  onChange={(event) =>
                    setFormState((current) => ({ ...current, title: event.target.value }))
                  }
                  maxLength={200}
                  required
                />
              </label>

              <label className="field">
                <span>Genre</span>
                <select
                  data-testid="story-genre-select"
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
                  data-testid="story-premise-input"
                  value={formState.premise}
                  onChange={(event) =>
                    setFormState((current) => ({ ...current, premise: event.target.value }))
                  }
                  minLength={10}
                  rows={5}
                  required
                />
              </label>

              <div className="story-form__grid">
                <label className="field">
                  <span>Target chapters</span>
                  <input
                    data-testid="story-target-chapters-input"
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
                    data-testid="story-audience-input"
                    value={formState.targetAudience}
                    onChange={(event) =>
                      setFormState((current) => ({
                        ...current,
                        targetAudience: event.target.value,
                      }))
                    }
                    maxLength={120}
                  />
                </label>
              </div>

              <label className="field">
                <span>Themes</span>
                <input
                  data-testid="story-themes-input"
                  value={formState.themes}
                  onChange={(event) =>
                    setFormState((current) => ({ ...current, themes: event.target.value }))
                  }
                  placeholder="betrayal, inheritance, grief"
                />
              </label>

              <label className="field">
                <span>Tone</span>
                <input
                  data-testid="story-tone-input"
                  value={formState.tone}
                  onChange={(event) =>
                    setFormState((current) => ({ ...current, tone: event.target.value }))
                  }
                  maxLength={200}
                />
              </label>

              <label className="story-toggle">
                <input
                  data-testid="story-publish-toggle"
                  type="checkbox"
                  checked={formState.publish}
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      publish: event.target.checked,
                    }))
                  }
                />
                <span>Publish after the initial full pipeline</span>
              </label>

              <div className="story-form__actions">
                <Button type="submit" disabled={isBusy} data-testid="story-create-draft">
                  Create draft
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={isBusy}
                  onClick={() => void launchPipeline()}
                  data-testid="story-run-pipeline"
                >
                  Run full pipeline
                </Button>
              </div>
            </form>
          </Panel>

          <Panel
            title="Project library"
            eyebrow="Current manuscripts"
            actions={
              <Button variant="ghost" onClick={() => void refreshLibrary()} disabled={isLoading}>
                {isLoading ? 'Refreshing...' : 'Refresh library'}
              </Button>
            }
            testId="story-library-panel"
          >
            <div className="story-library-summary" data-testid="story-library-summary">
              <strong>{stories.length} manuscript(s)</strong>
              <span>
                {activeStory
                  ? `Viewing ${activeStory.title}`
                  : 'Select a manuscript or create a new one.'}
              </span>
            </div>
            <ul className="story-list" data-testid="story-list">
              {stories.length === 0 ? (
                <li className="story-empty">No manuscripts yet. Create the first draft above.</li>
              ) : (
                stories.map((story) => {
                  const isActive = story.id === activeStoryId;

                  return (
                    <li
                      key={story.id}
                      className={`story-card${isActive ? ' story-card--active' : ''}`}
                    >
                      <button
                        className="story-card__button"
                        type="button"
                        onClick={() => void handleStorySelect(story.id)}
                        data-testid={`story-item-${story.id}`}
                      >
                        <div className="story-card__header">
                          <strong>{story.title}</strong>
                          <StatusPill tone={storyTone(story.status)}>
                            {storyStatusLabel(story.status)}
                          </StatusPill>
                        </div>
                        <p className="story-card__meta">
                          {story.genre} / {story.chapter_count} chapters / updated{' '}
                          {formatDate(story.updated_at)}
                        </p>
                      </button>
                    </li>
                  );
                })
              )}
            </ul>
          </Panel>
        </div>

        <div className="story-workbench__column story-workbench__column--wide">
          <Panel
            title="Current manuscript"
            eyebrow="Surface 2"
            testId="story-manuscript-panel"
          >
            {activeStory && workspace ? (
              <div className="story-manuscript">
                <div className="story-manuscript__summary">
                  <div>
                    <h2 className="story-manuscript__title" data-testid="story-active-title">
                      {activeStory.title}
                    </h2>
                    <p className="story-manuscript__copy">
                      {workflow?.premise ?? activeStory.metadata.premise_summary ?? 'Premise pending'}
                    </p>
                  </div>
                  <div className="story-manuscript__badges">
                    <StatusPill tone={storyTone(activeStory.status)}>
                      {storyStatusLabel(activeStory.status)}
                    </StatusPill>
                    <StatusPill tone={reviewTone(publishGatePassed)}>
                      {publishGatePassed ? 'publish ready' : 'needs revision'}
                    </StatusPill>
                  </div>
                </div>

                <p className="story-panel-note">
                  The center surface stays mutable: blueprint, outline, drafting progress, and the
                  current manuscript snapshot update here. Historical runs stay in the release desk.
                </p>

                <dl className="story-stats">
                  <div>
                    <dt>Target chapters</dt>
                    <dd>{targetChapters}</dd>
                  </div>
                  <div>
                    <dt>Chapters drafted</dt>
                    <dd>{activeStory.chapter_count}</dd>
                  </div>
                  <div>
                    <dt>Active characters</dt>
                    <dd>{selectedCharacterCount}</dd>
                  </div>
                  <div>
                    <dt>Chapter summaries</dt>
                    <dd>{chapterSummaryCount}</dd>
                  </div>
                </dl>

                <dl className="story-stats story-stats--compact">
                  <div>
                    <dt>Blueprint source</dt>
                    <dd>{blueprintSource}</dd>
                  </div>
                  <div>
                    <dt>Outline source</dt>
                    <dd>{outlineSource}</dd>
                  </div>
                  <div>
                    <dt>Semantic source</dt>
                    <dd>{semanticSource}</dd>
                  </div>
                  <div>
                    <dt>Mutable run</dt>
                    <dd>{activeRunLabel}</dd>
                  </div>
                </dl>

                <div className="story-tag-row">
                  {(activeStory.themes.length > 0 ? activeStory.themes : ['no themes yet']).map(
                    (theme) => (
                      <span key={theme} className="story-tag">
                        {theme}
                      </span>
                    ),
                  )}
                </div>

                <div className="story-memory-grid">
                  <article className="story-memory-card">
                    <h3>Run state</h3>
                    <p>{runState ? `${runState.mode} / ${runState.status}` : 'No active run'}</p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Run history</h3>
                    <p>{runHistory.length}</p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Blueprint</h3>
                    <p>{workspace.blueprint ? workspace.blueprint.premise_summary : 'Not generated yet'}</p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Continuity</h3>
                    <p>
                      {structuralReview?.metrics
                        ? `${structuralReview.metrics.continuity_score} / 100`
                        : 'Not reviewed yet'}
                    </p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Reader pull</h3>
                    <p>
                      {semanticReview?.metrics
                        ? `${semanticReview.metrics.reader_pull_score} / 100`
                        : 'Not reviewed yet'}
                    </p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Unresolved hooks</h3>
                    <p>{unresolvedHookEntries.length}</p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Artifacts</h3>
                    <p>{artifactHistory.length}</p>
                  </article>
                </div>

                <h3 className="story-section-title">Chapter map</h3>
                <div className="story-tag-row">
                  {workspace.memory.world_rules.length === 0 ? (
                    <span className="story-tag">world rules pending</span>
                  ) : (
                    workspace.memory.world_rules.slice(0, 4).map((rule) => (
                      <span key={rule.rule} className="story-tag">
                        {rule.rule}
                      </span>
                    ))
                  )}
                </div>

                <div className="story-workflow__actions">
                  <Button
                    type="button"
                    onClick={() => void generateBlueprint()}
                    disabled={!activeStory || isBusy}
                    data-testid="story-generate-blueprint"
                  >
                    Generate blueprint
                  </Button>
                </div>
              </div>
            ) : (
              <p className="story-empty">
                Select a manuscript from the library or create a new draft to begin.
              </p>
            )}
          </Panel>

          <Panel title="Outline" eyebrow="Stage 2" testId="story-outline-panel">
            {workspace ? (
              <div className="story-review">
                <div className="story-review__summary">
                  <StatusPill tone={stageTone(Boolean(workspace.outline), !canOutline)}>
                    {workspace.outline ? 'ready' : canOutline ? 'pending' : 'locked'}
                  </StatusPill>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => void generateOutline()}
                    disabled={!activeStory || isBusy || !canOutline}
                    data-testid="story-generate-outline"
                  >
                    Generate outline
                  </Button>
                </div>

                <p className="story-review__copy">
                  {workspace.outline
                    ? `已产出 ${workspace.outline.chapters.length} 个章节节点，默认节奏面向中文网文连载。`
                    : '大纲阶段负责章级推进、钩子布局和中长篇节奏分配。'}
                </p>

                <ul className="story-issue-list">
                  {(workspace.outline?.chapters ?? []).slice(0, 4).map((chapter) => (
                    <li key={chapter.chapter_number} className="story-chapter-card">
                      <div className="story-chapter-card__header">
                        <strong>Chapter {chapter.chapter_number}</strong>
                        <span>{chapter.hook ? 'hook set' : 'hook pending'}</span>
                      </div>
                      <h4>{chapter.title}</h4>
                      <p>{chapter.summary}</p>
                    </li>
                  ))}
                  {!workspace.outline ? (
                    <li className="story-empty">Generate the blueprint first to unlock the outline.</li>
                  ) : null}
                </ul>
              </div>
            ) : (
              <p className="story-empty">Create or select a manuscript first.</p>
            )}
          </Panel>

          <Panel title="Chapters / Scenes" eyebrow="Stage 3" testId="story-chapters-panel">
            {workspace ? (
              <div className="story-review">
                <div className="story-review__summary">
                  <StatusPill tone={stageTone(Boolean(activeStory?.chapter_count), !canDraft)}>
                    {activeStory?.chapter_count ? 'in progress' : canDraft ? 'pending' : 'locked'}
                  </StatusPill>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => void draftStory()}
                    disabled={!activeStory || isBusy || !canDraft}
                    data-testid="story-draft-chapters"
                  >
                    Draft chapters
                  </Button>
                </div>

                <ul className="story-chapter-list" data-testid="story-chapter-list">
                  {activeStory?.chapters.length ? (
                    activeStory.chapters.map((chapter) => (
                      (() => {
                        const chapterIssues = (review?.issues ?? []).filter((issue) =>
                          issueTargetsChapter(issue, chapter.chapter_number),
                        );
                        const hasRelationshipDebt = chapterIssues.some((issue) =>
                          RELATIONSHIP_DEBT_CODES.has(issue.code),
                        );
                        const hasHookDebt = chapterIssues.some((issue) =>
                          HOOK_DEBT_CODES.has(issue.code),
                        );

                        return (
                          <li key={chapter.id} className="story-chapter-card">
                            <div className="story-chapter-card__header">
                              <strong>Chapter {chapter.chapter_number}</strong>
                              <span>{chapter.scenes.length} scenes</span>
                            </div>
                            <h4>{chapter.title}</h4>
                            <p>{chapter.summary ?? 'No summary yet.'}</p>
                            {hasRelationshipDebt || hasHookDebt ? (
                              <div
                                className="story-tag-row"
                                data-testid={`story-chapter-debt-${chapter.chapter_number}`}
                              >
                                {hasRelationshipDebt ? (
                                  <span className="story-tag">relationship debt</span>
                                ) : null}
                                {hasHookDebt ? (
                                  <span className="story-tag">hook debt</span>
                                ) : null}
                              </div>
                            ) : null}
                            <div className="story-chapter-card__footer">
                              <span>{String(chapter.metadata.focus_character ?? 'No focus')}</span>
                              <span>Updated {formatDate(chapter.updated_at)}</span>
                            </div>
                          </li>
                        );
                      })()
                    ))
                  ) : (
                    <li className="story-empty">
                      Draft chapters to populate the manuscript map.
                    </li>
                  )}
                </ul>
              </div>
            ) : (
              <p className="story-empty">Create or select a manuscript first.</p>
            )}
          </Panel>
        </div>

        <div className="story-workbench__column">
          <Panel
            title="Run desk / release"
            eyebrow="Surface 3"
            testId="story-workflow-panel"
            actions={
              <Button variant="ghost" onClick={() => void refreshLibrary()} disabled={isLoading}>
                {isLoading ? 'Loading...' : 'Reload'}
              </Button>
            }
          >
            <div className="story-notes" data-testid="story-run-provenance">
              <h3>Run provenance</h3>
              <p>
                Keep the mutable manuscript and the selected immutable run separate. This panel is
                the release desk: rerun the active manuscript, inspect evidence, then export or
                publish with intent.
              </p>
              <dl className="story-stats story-stats--compact">
                <div>
                  <dt>Selected run</dt>
                  <dd>{selectedRunDetail?.run.run_id ?? 'None selected'}</dd>
                </div>
                <div>
                  <dt>Playback source</dt>
                  <dd>{selectedPlaybackSource}</dd>
                </div>
                <div>
                  <dt>Snapshot</dt>
                  <dd>{formatDate(selectedRunDetail?.latest_snapshot?.captured_at ?? null)}</dd>
                </div>
                <div>
                  <dt>Mutable run</dt>
                  <dd>{runState?.run_id ?? 'No active run'}</dd>
                </div>
              </dl>
            </div>

            <label className="story-toggle story-toggle--panel">
              <input
                data-testid="story-current-publish-toggle"
                type="checkbox"
                checked={rerunPublishes}
                onChange={(event) => setRerunPublishes(event.target.checked)}
                disabled={!activeStory || isBusy}
              />
              <span>
                Publish when rerunning the current manuscript ({rerunTargetChapters} target
                chapters)
              </span>
            </label>

            <div className="story-workflow__actions">
              <Button
                type="button"
                variant="secondary"
                onClick={() => void launchActivePipeline()}
                disabled={!activeStory || isBusy}
                data-testid="story-run-current-pipeline"
              >
                {rerunPublishes
                  ? 'Run current pipeline and publish'
                  : 'Run current pipeline'}
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => void exportStory()}
                disabled={!activeStory || isBusy || !canReview}
                data-testid="story-export"
              >
                Export
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => void publishStory()}
                disabled={!activeStory || isBusy || !canPublish}
                data-testid="story-publish"
              >
                Publish
              </Button>
            </div>

            <div className="story-console__state" data-testid="story-workflow-state">
              <strong>{isBusy ? 'Working...' : artifact.lastAction ?? 'Waiting for an action'}</strong>
              <span>{stories.length} manuscripts tracked</span>
            </div>

            {artifact.pipeline ? (
              <div className="story-pipeline-card" data-testid="story-pipeline-result">
                <h3>Pipeline result</h3>
                <dl className="story-stats">
                  <div>
                    <dt>Published</dt>
                    <dd>{artifact.pipeline.published ? 'yes' : 'no'}</dd>
                  </div>
                  <div>
                    <dt>Drafted chapters</dt>
                    <dd>{artifact.pipeline.drafted_chapters}</dd>
                  </div>
                  <div>
                    <dt>Initial review</dt>
                    <dd>{artifact.pipeline.initial_review.quality_score}</dd>
                  </div>
                  <div>
                    <dt>Final review</dt>
                    <dd>{artifact.pipeline.final_review.quality_score}</dd>
                  </div>
                </dl>
              </div>
            ) : null}

            {exportPayload ? (
              <div className="story-export-card" data-testid="story-export-summary">
                <h3>Export bundle</h3>
                <dl className="story-stats">
                  <div>
                    <dt>Workflow status</dt>
                    <dd>{exportPayload.workflow.status}</dd>
                  </div>
                  <div>
                    <dt>Blueprint</dt>
                    <dd>{exportPayload.blueprint ? 'included' : 'missing'}</dd>
                  </div>
                  <div>
                    <dt>Outline</dt>
                    <dd>{exportPayload.outline ? 'included' : 'missing'}</dd>
                  </div>
                  <div>
                    <dt>Exported</dt>
                    <dd>{formatDate(exportPayload.exported_at)}</dd>
                  </div>
                </dl>
              </div>
            ) : null}

            {runState?.stages.length ? (
              <ul className="story-issue-list">
                {runState.stages.map((stage) => (
                  <li key={stage.name + stage.started_at} className="story-chapter-card">
                    <div className="story-chapter-card__header">
                      <strong>{stage.name}</strong>
                      <StatusPill
                        tone={
                          stage.status === 'completed'
                            ? 'healthy'
                            : stage.status === 'failed'
                              ? 'offline'
                              : 'running'
                        }
                      >
                        {stage.status}
                      </StatusPill>
                    </div>
                    <p>{stageStatusLabel(stage)}</p>
                  </li>
                ))}
              </ul>
            ) : null}

            {latestRunEvent ? (
              <div className="story-notes">
                <h3>Latest run event</h3>
                <p>
                  {latestRunEvent.event_type}
                  {latestRunEvent.stage_name ? ` / ${latestRunEvent.stage_name}` : ''} at{' '}
                  {formatDate(latestRunEvent.timestamp)}
                </p>
              </div>
            ) : null}

            {runHistory.length ? (
              <div className="story-notes" data-testid="story-run-history">
                <h3>Run history</h3>
                <ul>
                  {runHistory.slice(-4).reverse().map((run) => (
                    <li key={run.run_id}>
                      <button
                        type="button"
                        className="story-card__button"
                        onClick={() =>
                          void selectRun(selectedRunId === run.run_id ? null : run.run_id)
                        }
                        data-testid={`story-run-item-${run.run_id}`}
                      >
                        <strong>
                          {selectedRunId === run.run_id ? 'Viewing' : 'Open'} {run.mode}
                        </strong>
                        <span>
                          {run.status} / {run.stages.length} stages /{' '}
                          {formatDate(run.completed_at ?? run.started_at)}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {selectedRunDetail ? (
              <div className="story-notes" data-testid="story-run-playback">
                <h3>Run playback</h3>
                <p>
                  {selectedRunDetail.run.mode} / {selectedRunDetail.run.status} / snapshot{' '}
                  {formatDate(selectedRunDetail.latest_snapshot?.captured_at ?? null)}
                </p>
                <dl className="story-stats" data-testid="story-run-playback-stats">
                  <div>
                    <dt>Artifacts</dt>
                    <dd>{selectedRunDetail.artifacts.length}</dd>
                  </div>
                  <div>
                    <dt>Events</dt>
                    <dd>{selectedRunDetail.events.length}</dd>
                  </div>
                  <div>
                    <dt>Snapshots</dt>
                    <dd>{selectedRunDetail.stage_snapshots.length}</dd>
                  </div>
                  <div>
                    <dt>Quality</dt>
                    <dd>{playbackReview?.quality_score ?? 0}</dd>
                  </div>
                  <div>
                    <dt>Reader pull</dt>
                    <dd>{playbackSemanticReview?.metrics?.reader_pull_score ?? 0}</dd>
                  </div>
                </dl>
                {playbackFailureMessage || selectedRunDetail.run.status === 'failed' ? (
                  <div className="story-notes" data-testid="story-run-failure">
                    <h3>Run failure</h3>
                    <p>
                      Failed stage: {playbackFailedStage ?? 'unknown'}
                      {selectedRunDetail.failure_code ? ` / ${selectedRunDetail.failure_code}` : ''}
                    </p>
                    <p>{playbackFailureMessage ?? 'No failure message recorded.'}</p>
                    <p>
                      Manuscript preserved:{' '}
                      {playbackManuscriptPreserved === false ? 'no' : 'yes'}
                    </p>
                    <p>Debug artifacts: {playbackFailureArtifacts.length}</p>
                    {playbackFailureArtifacts.length ? (
                      <ul>
                        {playbackFailureArtifacts.slice(-3).map((artifact) => (
                          <li key={artifact.artifact_id}>
                            {artifact.kind} v{artifact.version} / {artifact.source_provider}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                ) : null}
                {playbackRunEvent ? (
                  <p>
                    Latest playback event: {playbackRunEvent.event_type}
                    {playbackRunEvent.stage_name ? ` / ${playbackRunEvent.stage_name}` : ''}
                  </p>
                ) : null}
                <ul className="story-issue-list">
                  {selectedRunDetail.run.stages.map((stage) => (
                    <li key={stage.name + stage.started_at} className="story-chapter-card">
                      <div className="story-chapter-card__header">
                        <strong>{stage.name}</strong>
                        <StatusPill
                          tone={
                            stage.status === 'completed'
                              ? 'healthy'
                              : stage.status === 'failed'
                                ? 'offline'
                                : 'running'
                          }
                        >
                          {stage.status}
                        </StatusPill>
                      </div>
                      <p>{stageStatusLabel(stage)}</p>
                    </li>
                  ))}
                </ul>
                <div className="story-memory-grid">
                  <article className="story-memory-card" data-testid="story-playback-structural-gate">
                    <h3>Structural gate</h3>
                    <p>{playbackStructuralGatePassed ? 'pass' : 'blocked'}</p>
                  </article>
                  <article className="story-memory-card" data-testid="story-playback-semantic-gate">
                    <h3>Semantic gate</h3>
                    <p>{playbackSemanticGatePassed ? 'pass' : 'blocked'}</p>
                  </article>
                  <article className="story-memory-card" data-testid="story-playback-publish-gate">
                    <h3>Publish gate</h3>
                    <p>{playbackPublishGatePassed ? 'pass' : 'blocked'}</p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Blockers</h3>
                    <p>{playbackBlockingIssues.length}</p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Semantic blockers</h3>
                    <p>{playbackSemanticBlockingIssues.length}</p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Relationship debt</h3>
                    <p>{playbackRelationshipDebtIssues.length}</p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Hook debt</h3>
                    <p>{playbackHookDebtIssues.length}</p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Unresolved hooks</h3>
                    <p>{playbackUnresolvedHooks.length}</p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Overdue payoffs</h3>
                    <p>{playbackOverduePayoffs.length}</p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Strand gaps</h3>
                    <p>{playbackStrandGaps}</p>
                  </article>
                </div>
              </div>
            ) : null}

            {artifactHistory.length ? (
              <div className="story-notes" data-testid="story-artifact-history">
                <h3>Artifact history</h3>
                <ul>
                  {artifactHistory.slice(-4).reverse().map((entry) => (
                    <li key={entry.artifact_id}>
                      {entry.kind} v{entry.version} / {entry.source_provider} /{' '}
                      {formatDate(entry.generated_at)}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </Panel>

          <Panel
            title="Quality / publish gate"
            eyebrow="Review surface"
            testId="story-review-panel"
          >
            {workspace ? (
              <div className="story-review" data-testid="story-review-summary">
                <div className="story-review__summary">
                  <StatusPill tone={reviewTone(publishGatePassed)}>
                    {publishGatePassed ? 'publish ready' : canReview ? 'revision needed' : 'locked'}
                  </StatusPill>
                  <strong data-testid="story-review-score">{review?.quality_score ?? 0}</strong>
                </div>

                <div className="story-workflow__actions">
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => void reviewStory()}
                    disabled={!activeStory || isBusy || !canReview}
                    data-testid="story-review"
                  >
                    Review story
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => void reviseStory()}
                    disabled={!activeStory || isBusy || !canReview}
                    data-testid="story-revise"
                  >
                    Revise
                  </Button>
                </div>

                <p className="story-review__copy">
                  {review?.summary ??
                    'Run the review to score continuity, pacing, hooks, and drift signals.'}
                </p>

                {selectedRunDetail ? (
                  <p className="story-review__copy">
                    当前 Stage 4 展示的是最新 mutable workspace；上方 Run playback 展示的是所选 run 的 immutable snapshot。
                  </p>
                ) : null}

                <dl className="story-stats">
                  <div>
                    <dt>Continuity</dt>
                    <dd>{structuralReview?.metrics?.continuity_score ?? 0}</dd>
                  </div>
                  <div>
                    <dt>Pacing</dt>
                    <dd>{structuralReview?.metrics?.pacing_score ?? 0}</dd>
                  </div>
                  <div>
                    <dt>Reader pull</dt>
                    <dd>{semanticReview?.metrics?.reader_pull_score ?? 0}</dd>
                  </div>
                  <div>
                    <dt>Blockers</dt>
                    <dd>{blockingReviewIssues.length}</dd>
                  </div>
                </dl>

                <div className="story-memory-grid">
                  <article className="story-memory-card" data-testid="story-structural-gate">
                    <h3>Structural gate</h3>
                    <p>{structuralGatePassed ? 'pass' : 'blocked'}</p>
                  </article>
                  <article className="story-memory-card" data-testid="story-semantic-gate">
                    <h3>Semantic gate</h3>
                    <p>{semanticGatePassed ? 'pass' : 'blocked'}</p>
                  </article>
                  <article className="story-memory-card" data-testid="story-publish-gate">
                    <h3>Publish gate</h3>
                    <p>{publishGatePassed ? 'pass' : 'blocked'}</p>
                  </article>
                </div>

                <div className="story-memory-grid" data-testid="story-debt-signals">
                  <article className="story-memory-card">
                    <h3>Relationship debt</h3>
                    <p data-testid="story-relationship-debt-count">
                      {relationshipDebtIssues.length}
                    </p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Hook payoff debt</h3>
                    <p data-testid="story-hook-debt-count">{hookDebtIssues.length}</p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Unresolved promises</h3>
                    <p>{unresolvedPromiseEntries.length}</p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Overdue payoffs</h3>
                    <p>{overduePayoffEntries.length}</p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Strand gaps</h3>
                    <p>{activeStrandGaps}</p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Semantic blockers</h3>
                    <p>{semanticBlockingIssues.length}</p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Relationship states</h3>
                    <p>{workspace.memory.relationship_states.length}</p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Unresolved hooks</h3>
                    <p>{unresolvedHookEntries.length}</p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Plot clarity</h3>
                    <p>{semanticReview?.metrics?.plot_clarity_score ?? 0}</p>
                  </article>
                  <article className="story-memory-card">
                    <h3>OOC risk</h3>
                    <p>{semanticReview?.metrics?.ooc_risk_score ?? 0}</p>
                  </article>
                </div>

                {highlightedDebtIssues.length > 0 ? (
                  <div className="story-notes" data-testid="story-debt-issue-list">
                    <h3>Debt signals</h3>
                    <ul>
                      {highlightedDebtIssues.slice(0, 6).map((issue) => (
                        <li key={issue.code + issue.message}>
                          {issue.code}: {issue.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {(unresolvedPromiseEntries.length > 0 ||
                  semanticBlockingIssues.length > 0 ||
                  activeStrandGaps > 0) ? (
                  <div className="story-notes" data-testid="story-quality-timeline">
                    <h3>Quality timeline</h3>
                    <ul>
                      {unresolvedPromiseEntries.slice(0, 4).map((entry) => (
                        <li key={entry.promise_id}>
                          promise {entry.chapter_number}: {entry.promise}
                        </li>
                      ))}
                      {semanticBlockingIssues.slice(0, 4).map((issue) => (
                        <li key={issue.code + issue.message}>
                          semantic {issue.code}: {issue.message}
                        </li>
                      ))}
                      {activeStrandGaps > 0 ? (
                        <li>strand gap: {activeStrandGaps} line(s) need reactivation.</li>
                      ) : null}
                    </ul>
                  </div>
                ) : null}

                <ul className="story-issue-list" data-testid="story-issue-list">
                  {review?.issues.length ? (
                    review.issues.map((issue) => (
                      <li key={issue.code + issue.message} className={`story-issue story-issue--${issue.severity}`}>
                        <div className="story-issue__header">
                          <strong>{issue.code}</strong>
                          <StatusPill tone={issue.severity === 'blocker' ? 'offline' : 'degraded'}>
                            {issue.severity}
                          </StatusPill>
                        </div>
                        <p>{issue.message}</p>
                        {issue.suggestion ? <small>{issue.suggestion}</small> : null}
                      </li>
                    ))
                  ) : (
                    <li className="story-empty">
                      {canReview ? 'No blocking continuity issues.' : 'Draft chapters before review.'}
                    </li>
                  )}
                </ul>

                {workspace.revision_notes.length > 0 ? (
                  <div className="story-notes">
                    <h3>Revision notes</h3>
                    <ul>
                      {workspace.revision_notes.map((note) => (
                        <li key={note}>{note}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            ) : (
              <p className="story-empty">
                Review the manuscript to surface continuity issues and publish readiness.
              </p>
            )}
          </Panel>
        </div>
      </section>
    </main>
  );
}
