import { useState, type FormEvent } from 'react';

import { Button } from '@/components/Button';
import { Panel } from '@/components/Panel';
import { StatusPill } from '@/components/StatusPill';
import type {
  StoryCreateRequest,
  StoryGenre,
  StoryMemory,
  StoryPipelineRequest,
  StorySnapshot,
  StoryWorkflowState,
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function readWorkflow(story: StorySnapshot | null): StoryWorkflowState | null {
  if (!story || !isRecord(story.metadata.workflow)) {
    return null;
  }

  return story.metadata.workflow as StoryWorkflowState;
}

function readMemory(story: StorySnapshot | null): StoryMemory | null {
  if (!story || !isRecord(story.metadata.story_memory)) {
    return null;
  }

  return story.metadata.story_memory as StoryMemory;
}

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

export function StoryWorkbenchPage() {
  const { session, signOut } = useAuth();
  const [formState, setFormState] = useState<ComposerState>(initialComposerState);

  if (!session) {
    return null;
  }

  const {
    stories,
    activeStoryId,
    activeStory,
    artifact,
    isLoading,
    isBusy,
    error,
    refreshLibrary,
    selectStory,
    createStory,
    generateBlueprint,
    generateOutline,
    draftStory,
    reviewStory,
    reviseStory,
    exportStory,
    publishStory,
    runPipeline,
  } = useStoryWorkbench(session.workspaceId);

  const workflow = readWorkflow(activeStory);
  const memory = readMemory(activeStory);

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

  const selectedCharacterCount = memory?.active_characters?.length ?? 0;
  const chapterSummaryCount = memory?.chapter_summaries?.length ?? 0;
  const chapterMemory = workflow?.chapter_memory ?? [];
  const targetChapters = workflow?.target_chapters ?? formState.targetChapters;

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
              ? `Chapter ${activeStory.chapter_count} is the current working set. The workflow memory keeps the bible, outline, continuity check, and export bundle in sync.`
              : 'Create a draft, generate a blueprint, outline the arc, draft chapters, and keep continuity under review.'}
          </p>
        </div>

        <div className="story-workbench__hero-meta">
          <StatusPill tone={session.kind === 'guest' ? 'idle' : 'running'}>
            {session.kind === 'guest' ? 'guest session' : 'signed in'}
          </StatusPill>
          <StatusPill tone={storyTone(activeStory?.status)}>
            {storyStatusLabel(activeStory?.status)}
          </StatusPill>
          <StatusPill tone={reviewTone(artifact.review?.ready_for_publish)}>
            {artifact.review?.ready_for_publish ? 'publish ready' : 'review pending'}
          </StatusPill>
          <span className="story-workbench__workspace" data-testid="workspace-badge">
            {session.workspaceId}
          </span>
          <Button variant="ghost" onClick={signOut}>
            Sign out
          </Button>
        </div>
      </header>

      {error ? <p className="form-error">{error}</p> : null}

      <section className="story-workbench__layout">
        <div className="story-workbench__column">
          <Panel
            title="Create manuscript"
            eyebrow="Project seed"
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
                <span>Publish after running the pipeline</span>
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
            eyebrow="Manuscripts"
            actions={
              <Button variant="ghost" onClick={() => void refreshLibrary()} disabled={isLoading}>
                {isLoading ? 'Refreshing...' : 'Refresh library'}
              </Button>
            }
            testId="story-library-panel"
          >
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
            title="Selected manuscript"
            eyebrow="Narrative state"
            testId="story-manuscript-panel"
          >
            {activeStory ? (
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
                    <StatusPill tone={reviewTone(artifact.review?.ready_for_publish)}>
                      {artifact.review?.ready_for_publish ? 'publish ready' : 'needs revision'}
                    </StatusPill>
                  </div>
                </div>

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
                    <h3>Workflow status</h3>
                    <p>{workflow?.status ?? activeStory.status}</p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Blueprint</h3>
                    <p>{artifact.blueprint ? artifact.blueprint.premise_summary : 'Not generated yet'}</p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Outline</h3>
                    <p>
                      {artifact.outline
                        ? `${artifact.outline.chapters.length} chapters outlined`
                        : 'Not generated yet'}
                    </p>
                  </article>
                  <article className="story-memory-card">
                    <h3>Revision notes</h3>
                    <p>{artifact.revisionNotes.length > 0 ? artifact.revisionNotes[0] : 'None yet'}</p>
                  </article>
                </div>

                <h3 className="story-section-title">Chapter map</h3>
                <ul className="story-chapter-list" data-testid="story-chapter-list">
                  {activeStory.chapters.length === 0 ? (
                    <li className="story-empty">
                      Draft chapters to populate the manuscript map.
                    </li>
                  ) : (
                    activeStory.chapters.map((chapter) => {
                      const chapterMemoryEntry = chapterMemory.find((entry) => {
                        if (!isRecord(entry)) {
                          return false;
                        }

                        return Number(entry.chapter_number) === chapter.chapter_number;
                      });
                      const focusCharacter = isRecord(chapterMemoryEntry)
                        ? String(chapterMemoryEntry.focus_character ?? '')
                        : '';
                      const sceneCount = chapter.scenes.length;

                      return (
                        <li key={chapter.id} className="story-chapter-card">
                          <div className="story-chapter-card__header">
                            <strong>Chapter {chapter.chapter_number}</strong>
                            <span>{sceneCount} scenes</span>
                          </div>
                          <h4>{chapter.title}</h4>
                          <p>{chapter.summary ?? 'No summary yet.'}</p>
                          <div className="story-chapter-card__footer">
                            {focusCharacter ? <span>Focus: {focusCharacter}</span> : <span />}
                            <span>Updated {formatDate(chapter.updated_at)}</span>
                          </div>
                        </li>
                      );
                    })
                  )}
                </ul>
              </div>
            ) : (
              <p className="story-empty">
                Select a manuscript from the library or create a new draft to begin.
              </p>
            )}
          </Panel>
        </div>

        <div className="story-workbench__column">
          <Panel
            title="Workflow console"
            eyebrow="Generation stages"
            testId="story-workflow-panel"
            actions={
              <Button variant="ghost" onClick={() => void refreshLibrary()} disabled={isLoading}>
                {isLoading ? 'Loading...' : 'Reload'}
              </Button>
            }
          >
            <div className="story-workflow__actions">
              <Button
                type="button"
                onClick={() => void generateBlueprint()}
                disabled={!activeStory || isBusy}
                data-testid="story-generate-blueprint"
              >
                Generate blueprint
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => void generateOutline()}
                disabled={!activeStory || isBusy || !artifact.blueprint}
                data-testid="story-generate-outline"
              >
                Generate outline
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => void draftStory()}
                disabled={!activeStory || isBusy || !artifact.outline}
                data-testid="story-draft-chapters"
              >
                Draft chapters
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => void reviewStory()}
                disabled={!activeStory || isBusy || activeStory.chapter_count === 0}
                data-testid="story-review"
              >
                Review story
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => void reviseStory()}
                disabled={!activeStory || isBusy || activeStory.chapter_count === 0}
                data-testid="story-revise"
              >
                Revise
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => void exportStory()}
                disabled={!activeStory || isBusy || activeStory.chapter_count === 0}
                data-testid="story-export"
              >
                Export
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => void publishStory()}
                disabled={!activeStory || isBusy || !artifact.review?.ready_for_publish}
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
          </Panel>

          <Panel
            title="Continuity report"
            eyebrow="Quality gate"
            testId="story-review-panel"
          >
            {artifact.review ? (
              <div className="story-review" data-testid="story-review">
                <div className="story-review__summary">
                  <StatusPill tone={reviewTone(artifact.review.ready_for_publish)}>
                    {artifact.review.ready_for_publish ? 'publish ready' : 'revision needed'}
                  </StatusPill>
                  <strong data-testid="story-review-score">{artifact.review.quality_score}</strong>
                </div>

                <p className="story-review__copy">{artifact.review.summary}</p>

                <dl className="story-stats">
                  <div>
                    <dt>Issues</dt>
                    <dd>{artifact.review.issues.length}</dd>
                  </div>
                  <div>
                    <dt>Chapters</dt>
                    <dd>{artifact.review.chapter_count}</dd>
                  </div>
                  <div>
                    <dt>Scenes</dt>
                    <dd>{artifact.review.scene_count}</dd>
                  </div>
                  <div>
                    <dt>Checked</dt>
                    <dd>{formatDate(artifact.review.checked_at)}</dd>
                  </div>
                </dl>

                <ul className="story-issue-list" data-testid="story-issue-list">
                  {artifact.review.issues.length === 0 ? (
                    <li className="story-empty">No blocking continuity issues.</li>
                  ) : (
                    artifact.review.issues.map((issue) => (
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
                  )}
                </ul>

                {artifact.review.revision_notes.length > 0 ? (
                  <div className="story-notes">
                    <h3>Revision notes</h3>
                    <ul>
                      {artifact.review.revision_notes.map((note) => (
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

            {artifact.exportPayload ? (
              <div className="story-export-card" data-testid="story-export-summary">
                <h3>Export bundle</h3>
                <dl className="story-stats">
                  <div>
                    <dt>Workflow status</dt>
                    <dd>{String(artifact.exportPayload.workflow.status ?? 'unknown')}</dd>
                  </div>
                  <div>
                    <dt>Blueprint</dt>
                    <dd>{artifact.exportPayload.blueprint ? 'included' : 'missing'}</dd>
                  </div>
                  <div>
                    <dt>Outline</dt>
                    <dd>{artifact.exportPayload.outline ? 'included' : 'missing'}</dd>
                  </div>
                  <div>
                    <dt>Revision notes</dt>
                    <dd>{artifact.exportPayload.revision_notes.length}</dd>
                  </div>
                </dl>
              </div>
            ) : null}
          </Panel>
        </div>
      </section>
    </main>
  );
}
