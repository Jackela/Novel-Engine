import { afterEach, describe, expect, it, vi } from 'vitest';
import { act } from 'react';

import { api } from '@/app/api';

import { render, screen, waitFor } from '../../../tests/test-utils';
import { useStoryWorkbench } from './useStoryWorkbench';
import type {
  StoryBlueprint,
  StoryHybridReviewReport,
  StoryOutline,
  StoryPipelineResult,
  StorySemanticReviewReport,
  StoryReviewReport,
  StoryRunDetailResponse,
  StoryRunsResponse,
  StorySnapshot,
  StoryWorkflowState,
  StoryWorkspace,
} from '@/app/types';

function makeStory(title: string, status: StorySnapshot['status'] = 'draft'): StorySnapshot {
  return {
    id: `${title.toLowerCase().replace(/\s+/g, '-')}-id`,
    title,
    genre: 'fantasy',
    author_id: 'workspace-123',
    status,
    chapters: [],
    chapter_count: 0,
    current_chapter_id: null,
    target_audience: null,
    themes: [],
    metadata: {},
    created_at: '2024-01-01T00:00:00.000Z',
    updated_at: '2024-01-01T00:00:00.000Z',
  };
}

function makePipelineResult(title: string): StoryPipelineResult {
  const storyId = `${title.toLowerCase().replace(/\s+/g, '-')}-id`;
  const blueprint: StoryBlueprint = {
    step: 'bible',
    provider: 'mock',
    model: 'deterministic-story-v1',
    generated_at: '2024-01-01T00:00:00.000Z',
    story_id: storyId,
    version: 1,
    world_bible: {},
    character_bible: {},
    premise_summary: 'A premise',
  };
  const outline: StoryOutline = {
    step: 'outline',
    provider: 'mock',
    model: 'deterministic-story-v1',
    generated_at: '2024-01-01T00:00:00.000Z',
    target_chapters: 3,
    version: 1,
    chapters: [],
  };
  const structuralReview: StoryReviewReport = {
    artifact_id: 'review-1',
    version: 1,
    source_run_id: 'run-1',
    source_provider: 'system',
    source_model: 'continuity-review-v1',
    story_id: storyId,
    quality_score: 100,
    ready_for_publish: true,
    summary: 'Story passes the publication gate.',
    issues: [],
    revision_notes: ['Repaired the hook'],
    chapter_count: 3,
    scene_count: 1,
    continuity_checks: {},
    checked_at: '2024-01-01T00:00:00.000Z',
    metrics: {
      continuity_score: 100,
      pacing_score: 100,
      hook_score: 100,
      character_consistency_score: 100,
      timeline_consistency_score: 100,
    },
  };
  const semanticReview: StorySemanticReviewReport = {
    artifact_id: 'semantic-review-1',
    version: 1,
    source_run_id: 'run-1',
    source_provider: 'mock',
    source_model: 'deterministic-story-v1',
    story_id: storyId,
    semantic_score: 100,
    ready_for_publish: true,
    summary: 'Semantic review passes with strong serial pull.',
    issues: [],
    repair_suggestions: ['Maintain promise cadence.'],
    checked_at: '2024-01-01T00:00:00.000Z',
    metrics: {
      semantic_score: 100,
      reader_pull_score: 100,
      plot_clarity_score: 100,
      ooc_risk_score: 0,
    },
  };
  const review: StoryHybridReviewReport = {
    artifact_id: 'hybrid-review-1',
    version: 1,
    source_run_id: 'run-1',
    source_provider: 'system',
    source_model: 'hybrid-publication-gate-v1',
    story_id: storyId,
    quality_score: 100,
    ready_for_publish: true,
    summary: 'Story passes the hybrid publication gate.',
    structural_review: structuralReview,
    semantic_review: semanticReview,
    issues: [],
    blocked_by: [],
    checked_at: '2024-01-01T00:00:00.000Z',
  };
  const workflow: StoryWorkflowState = {
    schema_version: 1,
    status: 'published',
    premise: 'A premise',
    tone: 'commercial web fiction',
    target_chapters: 3,
    generation_trace: [],
    chapter_memory: [],
    revision_notes: ['Repaired the hook'],
    blueprint,
    blueprint_generated_at: '2024-01-01T00:00:00.000Z',
    outline,
    outline_generated_at: '2024-01-01T00:00:00.000Z',
    drafted_chapters: 3,
    last_structural_review: structuralReview,
    last_semantic_review: semanticReview,
    last_review: review,
    last_exported_at: null,
    last_updated_at: '2024-01-01T00:00:00.000Z',
    published_at: '2024-01-01T00:00:00.000Z',
    revision_history: [],
    run_state: null,
    current_run_id: null,
  };

  const story: StorySnapshot = {
    ...makeStory(title, 'active'),
    chapter_count: 3,
    chapters: [
      {
        id: 'chapter-1',
        story_id: storyId,
        chapter_number: 1,
        title: 'Chapter 1',
        summary: 'Opening tension',
        scenes: [],
        metadata: {},
        created_at: '2024-01-01T00:00:00.000Z',
        updated_at: '2024-01-01T00:00:00.000Z',
      },
    ],
    metadata: {},
    updated_at: '2024-01-01T00:00:00.000Z',
  };

  const workspace: StoryWorkspace = {
    story,
    workflow,
    memory: {
      schema_version: 1,
      premise: 'A premise',
      tone: 'commercial web fiction',
      target_chapters: 3,
      themes: [],
      chapter_summaries: [],
      active_characters: [],
      outline_titles: [],
      story_promises: [],
      timeline_ledger: [],
      hook_ledger: [],
      promise_ledger: [],
      payoff_beats: [],
      pacing_ledger: [],
      strand_ledger: [],
      character_states: [],
      relationship_states: [],
      world_rules: [],
      revision_notes: ['Repaired the hook'],
    },
    blueprint,
    outline,
    structural_review: structuralReview,
    semantic_review: semanticReview,
    hybrid_review: review,
    review,
    export: {
      artifact_id: 'export-1',
      version: 1,
      source_run_id: 'run-1',
      source_provider: 'system',
      source_model: 'workspace-export-v1',
      story,
      workflow: {
        ...workflow,
        last_exported_at: '2024-01-01T00:00:00.000Z',
      },
      memory: {
        schema_version: 1,
        premise: 'A premise',
        tone: 'commercial web fiction',
        target_chapters: 3,
        themes: [],
        chapter_summaries: [],
        active_characters: [],
        outline_titles: [],
        story_promises: [],
        timeline_ledger: [],
        hook_ledger: [],
        promise_ledger: [],
        payoff_beats: [],
        pacing_ledger: [],
        strand_ledger: [],
        character_states: [],
        relationship_states: [],
        world_rules: [],
        revision_notes: ['Repaired the hook'],
      },
      blueprint,
      outline,
      last_review: structuralReview,
      revision_notes: ['Repaired the hook'],
      exported_at: '2024-01-01T00:00:00.000Z',
    },
    revision_notes: ['Repaired the hook'],
    run: null,
    run_history: [],
    run_events: [],
    artifact_history: [],
  };

  return {
    story,
    workspace,
    blueprint,
    outline,
    drafted_chapters: 3,
    initial_review: review,
    revision_notes: ['Repaired the hook'],
    final_review: review,
    export: workspace.export!,
    published: true,
  };
}

function makeRunDetail(title: string): StoryRunDetailResponse {
  const pipeline = makePipelineResult(title);
  return {
    operation: 'pipeline',
    run: {
      run_id: 'run-1',
      mode: 'pipeline',
      status: 'completed',
      started_at: '2024-01-01T00:00:00.000Z',
      completed_at: '2024-01-01T00:00:00.000Z',
      published: false,
      stages: [],
    },
    events: [],
    artifacts: [],
    latest_snapshot: {
      snapshot_id: 'snapshot-1',
      story_id: pipeline.story.id,
      run_id: 'run-1',
      snapshot_type: 'run_completed',
      captured_at: '2024-01-01T00:00:00.000Z',
      stage_name: null,
      workspace: pipeline.workspace,
    },
    stage_snapshots: [],
  };
}

function makeRunsResponse(title: string): StoryRunsResponse {
  const runDetail = makeRunDetail(title);
  return {
    current_run: runDetail.run,
    runs: [runDetail.run],
  };
}

function StoryWorkbenchProbe({ authorId }: { authorId: string }) {
  const {
    stories,
    activeStory,
    currentRun,
    runSummaries,
    selectedRunId,
    selectedRunDetail,
    artifact,
    createStory,
    runPipeline,
    runStoryPipeline,
  } =
    useStoryWorkbench(authorId);

  return (
    <div>
      <span data-testid="story-count">{stories.length}</span>
      <span data-testid="story-title">{activeStory?.title ?? 'none'}</span>
      <span data-testid="current-run">{currentRun?.run_id ?? 'none'}</span>
      <span data-testid="run-summary-count">{runSummaries.length}</span>
      <span data-testid="selected-run-id">{selectedRunId ?? 'none'}</span>
      <span data-testid="selected-run-snapshot">
        {selectedRunDetail?.latest_snapshot?.snapshot_id ?? 'none'}
      </span>
      <span data-testid="story-action">{artifact.lastAction ?? 'none'}</span>
      <button
        data-testid="create-story"
        onClick={() =>
          void createStory({
            title: 'Hook Story',
            genre: 'fantasy',
            premise: 'A courier maps a city that keeps moving at dawn.',
            target_chapters: 3,
            author_id: authorId,
          })
        }
        type="button"
      >
        Create
      </button>
      <button
        data-testid="run-pipeline"
        onClick={() =>
          void runPipeline({
            title: 'Pipeline Hook Story',
            genre: 'fantasy',
            premise: 'A courier maps a city that keeps moving at dawn.',
            target_chapters: 3,
            author_id: authorId,
            publish: true,
          })
        }
        type="button"
      >
        Pipeline
      </button>
      <button
        data-testid="run-current-pipeline"
        onClick={() => void runStoryPipeline({ publish: false, targetChapters: 3 })}
        type="button"
      >
        Current Pipeline
      </button>
    </div>
  );
}

describe('useStoryWorkbench', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('creates a story and runs the pipeline using the canonical author id', async () => {
    vi.spyOn(api, 'listStories').mockResolvedValue({
      stories: [],
      count: 0,
      limit: 20,
      offset: 0,
    });
    vi.spyOn(api, 'createStory').mockResolvedValue({
      story: makeStory('Hook Story'),
    });
    vi.spyOn(api, 'getStoryWorkspace').mockResolvedValue({
      workspace: {
        ...makePipelineResult('Hook Story').workspace,
        story: makeStory('Hook Story'),
      },
    });
    vi.spyOn(api, 'runPipeline').mockResolvedValue(makePipelineResult('Pipeline Hook Story'));
    vi.spyOn(api, 'getStoryRuns').mockResolvedValue(makeRunsResponse('Pipeline Hook Story'));

    render(<StoryWorkbenchProbe authorId="workspace-123" />);

    await waitFor(() => {
      expect(screen.getByTestId('story-count')).toHaveTextContent('0');
    });

    await act(async () => {
      screen.getByTestId('create-story').click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('story-title')).toHaveTextContent('Hook Story');
      expect(screen.getByTestId('story-action')).toHaveTextContent('Created draft manuscript');
    });

    await act(async () => {
      screen.getByTestId('run-pipeline').click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('story-title')).toHaveTextContent('Pipeline Hook Story');
      expect(screen.getByTestId('current-run')).toHaveTextContent('run-1');
      expect(screen.getByTestId('run-summary-count')).toHaveTextContent('1');
      expect(screen.getByTestId('story-action')).toHaveTextContent(
        'Completed pipeline and published story',
      );
    });
  });

  it('re-runs the pipeline for the currently selected story', async () => {
    vi.spyOn(api, 'listStories').mockResolvedValue({
      stories: [],
      count: 0,
      limit: 20,
      offset: 0,
    });
    vi.spyOn(api, 'createStory').mockResolvedValue({
      story: makeStory('Hook Story'),
    });
    vi.spyOn(api, 'getStoryWorkspace').mockResolvedValue({
      workspace: {
        ...makePipelineResult('Hook Story').workspace,
        story: makeStory('Hook Story'),
      },
    });
    vi.spyOn(api, 'createStoryRun').mockResolvedValue(makeRunDetail('Hook Story'));
    vi.spyOn(api, 'getStoryRuns').mockResolvedValue(makeRunsResponse('Hook Story'));

    render(<StoryWorkbenchProbe authorId="workspace-123" />);

    await waitFor(() => {
      expect(screen.getByTestId('story-count')).toHaveTextContent('0');
    });

    await act(async () => {
      screen.getByTestId('create-story').click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('story-title')).toHaveTextContent('Hook Story');
    });

    await act(async () => {
      screen.getByTestId('run-current-pipeline').click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('story-action')).toHaveTextContent(
        'Re-ran pipeline for current story',
      );
      expect(screen.getByTestId('current-run')).toHaveTextContent('run-1');
      expect(screen.getByTestId('selected-run-id')).toHaveTextContent('run-1');
      expect(screen.getByTestId('selected-run-snapshot')).toHaveTextContent('snapshot-1');
    });
  });
});
