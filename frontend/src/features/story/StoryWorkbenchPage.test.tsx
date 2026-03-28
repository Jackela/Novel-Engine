import { afterEach, describe, expect, it, vi } from 'vitest';

import type {
  StoryArtifactHistoryEntry,
  SessionState,
  StoryHybridReviewReport,
  StorySemanticReviewReport,
  StoryReviewReport,
  StoryRunState,
  StoryRunSnapshot,
  StoryRunDetailResponse,
  StorySnapshot,
  StoryWorkspace,
  StoryWorkflowState,
} from '@/app/types';
import { render, screen } from '../../../tests/test-utils';
import { useAuth } from '@/features/auth/useAuth';

import { StoryWorkbenchPage } from './StoryWorkbenchPage';
import type { UseStoryWorkbenchResult } from './useStoryWorkbench';
import { useStoryWorkbench } from './useStoryWorkbench';

vi.mock('@/features/auth/useAuth', () => ({
  useAuth: vi.fn(),
}));

vi.mock('./useStoryWorkbench', () => ({
  useStoryWorkbench: vi.fn(),
}));

function makeStoryWorkspace(): StoryWorkspace {
  const structuralReview: StoryReviewReport = {
    artifact_id: 'review-1',
    version: 2,
    source_run_id: 'run-2',
    source_provider: 'system',
    source_model: 'continuity-review-v1',
    story_id: 'story-1',
    quality_score: 82,
    ready_for_publish: false,
    summary: 'Story needs 1 blocker(s) and 3 warning(s) addressed.',
    issues: [
      {
        code: 'relationship_drift',
        severity: 'blocker',
        message: 'Chapter 2 no longer reflects the intended alliance beat.',
        location: 'chapter-2',
        suggestion: 'Re-anchor the alliance conflict.',
        details: {},
      },
      {
        code: 'missing_relationship_state',
        severity: 'warning',
        message: 'Chapter 4 is missing relationship state metadata.',
        location: 'chapter-4',
        suggestion: 'Store the relationship state during drafting.',
        details: {},
      },
      {
        code: 'missing_hook_payoff',
        severity: 'warning',
        message: 'Chapter 3 does not pay off the previous hook.',
        location: 'chapter-3',
        suggestion: 'Open by escalating the prior hook.',
        details: {},
      },
      {
        code: 'hook_debt',
        severity: 'warning',
        message: 'Hook debt is accumulating in late arc chapters.',
        location: 'story',
        suggestion: 'Strengthen the affected endings.',
        details: {
          chapters: [3, 4],
        },
      },
    ],
    revision_notes: ['Repair relationship beat in chapter 2'],
    chapter_count: 4,
    scene_count: 12,
    continuity_checks: {},
    checked_at: '2024-01-01T00:00:00.000Z',
    metrics: {
      continuity_score: 81,
      pacing_score: 78,
      hook_score: 74,
      character_consistency_score: 83,
      timeline_consistency_score: 88,
    },
  };
  const semanticReview: StorySemanticReviewReport = {
    artifact_id: 'semantic-review-1',
    version: 1,
    source_run_id: 'run-2',
    source_provider: 'mock',
    source_model: 'deterministic-story-v1',
    story_id: 'story-1',
    semantic_score: 79,
    ready_for_publish: false,
    summary: 'Reader pull softens in the late arc and one alliance beat feels unstable.',
    issues: [
      {
        code: 'relationship_progression_stall',
        severity: 'blocker',
        message: 'Lin and Qiao stop evolving after chapter 2.',
        location: 'chapter-4',
        suggestion: 'Force a relationship re-negotiation beat.',
        details: {},
      },
      {
        code: 'weak_serial_pull',
        severity: 'warning',
        message: 'Chapter endings are not escalating enough.',
        location: 'story',
        suggestion: 'Strengthen the last-turn reveal.',
        details: {},
      },
    ],
    repair_suggestions: ['Escalate the alliance fracture with a public betrayal.'],
    checked_at: '2024-01-01T00:00:00.000Z',
    metrics: {
      semantic_score: 79,
      reader_pull_score: 76,
      plot_clarity_score: 84,
      ooc_risk_score: 28,
    },
  };
  const review: StoryHybridReviewReport = {
    artifact_id: 'hybrid-review-1',
    version: 1,
    source_run_id: 'run-2',
    source_provider: 'system',
    source_model: 'hybrid-publication-gate-v1',
    story_id: 'story-1',
    quality_score: 82,
    ready_for_publish: false,
    summary: 'Story is blocked by structural and semantic debt.',
    structural_review: structuralReview,
    semantic_review: semanticReview,
    issues: [...structuralReview.issues, ...semanticReview.issues],
    blocked_by: ['structural', 'semantic'],
    structural_gate_passed: false,
    semantic_gate_passed: false,
    publish_gate_passed: false,
    checked_at: '2024-01-01T00:00:00.000Z',
  };

  const workflow: StoryWorkflowState = {
    schema_version: 1,
    status: 'reviewed',
    premise: 'A courier maps a city that changes its streets every dawn.',
    tone: 'commercial web fiction',
    target_chapters: 12,
    generation_trace: [],
    chapter_memory: [],
    revision_notes: ['Repair relationship beat in chapter 2'],
    blueprint: null,
    blueprint_generated_at: null,
    outline: null,
    outline_generated_at: null,
    drafted_chapters: 4,
    last_structural_review: structuralReview,
    last_semantic_review: semanticReview,
    last_review: review,
    last_exported_at: null,
    last_updated_at: '2024-01-01T00:00:00.000Z',
    published_at: null,
    revision_history: [],
    run_state: null,
    current_run_id: 'run-2',
  };

  const story: StorySnapshot = {
    id: 'story-1',
    title: 'Debt Signal Story',
    genre: 'fantasy',
    author_id: 'workspace-123',
    status: 'active',
    chapters: [
      {
        id: 'chapter-1',
        story_id: 'story-1',
        chapter_number: 1,
        title: 'Chapter 1',
        summary: 'The map starts to move.',
        scenes: [],
        metadata: {
          focus_character: 'Lin',
        },
        created_at: '2024-01-01T00:00:00.000Z',
        updated_at: '2024-01-01T00:00:00.000Z',
      },
      {
        id: 'chapter-2',
        story_id: 'story-1',
        chapter_number: 2,
        title: 'Chapter 2',
        summary: 'An alliance starts to crack.',
        scenes: [],
        metadata: {
          focus_character: 'Lin',
        },
        created_at: '2024-01-01T00:00:00.000Z',
        updated_at: '2024-01-01T00:00:00.000Z',
      },
      {
        id: 'chapter-3',
        story_id: 'story-1',
        chapter_number: 3,
        title: 'Chapter 3',
        summary: 'The old promise comes due.',
        scenes: [],
        metadata: {
          focus_character: 'Lin',
        },
        created_at: '2024-01-01T00:00:00.000Z',
        updated_at: '2024-01-01T00:00:00.000Z',
      },
      {
        id: 'chapter-4',
        story_id: 'story-1',
        chapter_number: 4,
        title: 'Chapter 4',
        summary: 'A false victory shakes the crew.',
        scenes: [],
        metadata: {
          focus_character: 'Lin',
        },
        created_at: '2024-01-01T00:00:00.000Z',
        updated_at: '2024-01-01T00:00:00.000Z',
      },
    ],
    chapter_count: 4,
    current_chapter_id: 'chapter-4',
    target_audience: 'male 18-35',
    themes: ['betrayal', 'inheritance'],
    metadata: {},
    created_at: '2024-01-01T00:00:00.000Z',
    updated_at: '2024-01-01T00:00:00.000Z',
  };

  return {
    story,
    workflow,
    memory: {
      schema_version: 1,
      premise: workflow.premise,
      tone: workflow.tone,
      target_chapters: workflow.target_chapters,
      themes: story.themes,
      chapter_summaries: [],
      active_characters: ['Lin', 'Qiao'],
      outline_titles: [],
      story_promises: [
        {
          promise_id: 'promise-2',
          chapter_number: 2,
          text: 'Lin and Qiao must decide whether to expose the compass.',
          strand: 'fire',
          chapter_objective: 'Stress-test the alliance.',
          due_by_chapter: 4,
        },
      ],
      timeline_ledger: [
        { chapter_number: 1, timeline_day: 1, summary: 'Day 1' },
        { chapter_number: 2, timeline_day: 2, summary: 'Day 2' },
        { chapter_number: 3, timeline_day: 3, summary: 'Day 3' },
        { chapter_number: 4, timeline_day: 4, summary: 'Day 4' },
      ],
      hook_ledger: [
        { chapter_number: 1, hook: 'The map bleeds ink', surfaced: true },
        { chapter_number: 2, hook: 'Qiao hides the compass', surfaced: false },
        { chapter_number: 3, hook: 'The city opens a sealed gate', surfaced: false },
        { chapter_number: 4, hook: 'A judge returns from exile', surfaced: false },
      ],
      promise_ledger: [
        {
          chapter_number: 2,
          promise: 'Lin and Qiao must decide whether to expose the compass.',
          surfaced: true,
          promise_id: 'promise-2',
          strand: 'fire',
          chapter_objective: 'Stress-test the alliance.',
          payoff_chapter: null,
          due_by_chapter: 4,
          status: 'open',
        },
      ],
      payoff_beats: [],
      pacing_ledger: [
        {
          chapter_number: 2,
          phase: 'pressure',
          signature: 'alliance crack',
          tension: 78,
          hook_strength: 68,
          chapter_objective: 'Stress-test the alliance.',
        },
      ],
      strand_ledger: [
        { chapter_number: 1, strand: 'quest', status: 'active' },
        { chapter_number: 2, strand: 'fire', status: 'active' },
        { chapter_number: 3, strand: 'quest', status: 'active' },
      ],
      character_states: [
        { chapter_number: 1, name: 'Lin', motivation: 'Survive', role: 'lead' },
      ],
      relationship_states: [
        { chapter_number: 1, source: 'Lin', target: 'Qiao', status: 'tentative ally' },
        { chapter_number: 2, source: 'Lin', target: 'Qiao', status: 'strained ally' },
      ],
      world_rules: [{ rule: 'The city changes at dawn', source: 'blueprint' }],
      revision_notes: ['Repair relationship beat in chapter 2'],
    },
    blueprint: null,
    outline: null,
    structural_review: structuralReview,
    semantic_review: semanticReview,
    hybrid_review: review,
    review,
    export: null,
    revision_notes: ['Repair relationship beat in chapter 2'],
    run: null,
    run_history: [],
    run_events: [],
    artifact_history: [],
  };
}

function makePlaybackRunDetail(workspace: StoryWorkspace): StoryRunDetailResponse {
  const baseReview = workspace.review;
  if (!baseReview) {
    throw new Error('Expected workspace review to exist for playback.');
  }

  const playbackStructuralReview: StoryReviewReport = {
    ...(baseReview.structural_review ?? {
      artifact_id: 'review-playback',
      version: 1,
      source_run_id: 'run-immutable',
      source_provider: 'system',
      source_model: 'continuity-review-v1',
      story_id: workspace.story.id,
      quality_score: 97,
      ready_for_publish: true,
      summary: 'Playback structural review.',
      issues: [],
      revision_notes: [],
      chapter_count: workspace.story.chapter_count,
      scene_count: 0,
      continuity_checks: {},
      checked_at: '2024-01-01T00:00:00.000Z',
      metrics: {
        continuity_score: 97,
        pacing_score: 96,
        hook_score: 95,
        character_consistency_score: 98,
        timeline_consistency_score: 99,
      },
    }),
    quality_score: 97,
    ready_for_publish: true,
    summary: 'Story passes the structural publication gate.',
    issues: [],
    metrics: {
      continuity_score: 97,
      pacing_score: 96,
      hook_score: 95,
      character_consistency_score: 98,
      timeline_consistency_score: 99,
    },
  };
  const playbackSemanticReview: StorySemanticReviewReport = {
    ...(baseReview.semantic_review ?? {
      artifact_id: 'semantic-playback',
      version: 1,
      source_run_id: 'run-immutable',
      source_provider: 'mock',
      source_model: 'deterministic-story-v1',
      story_id: workspace.story.id,
      semantic_score: 97,
      ready_for_publish: true,
      summary: 'Playback semantic review.',
      issues: [],
      repair_suggestions: [],
      checked_at: '2024-01-01T00:00:00.000Z',
      metrics: {
        semantic_score: 97,
        reader_pull_score: 96,
        plot_clarity_score: 95,
        ooc_risk_score: 8,
      },
    }),
    semantic_score: 97,
    ready_for_publish: true,
    summary: 'Story keeps strong serial pull in playback.',
    issues: [],
    metrics: {
      semantic_score: 97,
      reader_pull_score: 96,
      plot_clarity_score: 95,
      ooc_risk_score: 8,
    },
  };
  const playbackReview: StoryHybridReviewReport = {
    ...baseReview,
    quality_score: 97,
    ready_for_publish: true,
    summary: 'Story passes the hybrid publication gate.',
    structural_review: playbackStructuralReview,
    semantic_review: playbackSemanticReview,
    issues: [],
    blocked_by: [],
    structural_gate_passed: true,
    semantic_gate_passed: true,
    publish_gate_passed: true,
  };
  const playbackWorkspace: StoryWorkspace = {
    ...workspace,
    structural_review: playbackStructuralReview,
    semantic_review: playbackSemanticReview,
    hybrid_review: playbackReview,
    review: playbackReview,
    workflow: {
      ...workspace.workflow,
      status: 'reviewed',
      last_structural_review: playbackStructuralReview,
      last_semantic_review: playbackSemanticReview,
      last_review: playbackReview,
    },
  };

  return {
    operation: 'pipeline',
    run: {
      run_id: 'run-immutable',
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
      story_id: workspace.story.id,
      run_id: 'run-immutable',
      snapshot_type: 'run_completed',
      captured_at: '2024-01-01T00:00:00.000Z',
      stage_name: null,
      workspace: playbackWorkspace,
    },
    stage_snapshots: [
      {
        snapshot_id: 'snapshot-2',
        story_id: workspace.story.id,
        run_id: 'run-immutable',
        snapshot_type: 'stage_completed',
        captured_at: '2024-01-01T00:00:00.000Z',
        stage_name: 'blueprint',
        workspace: playbackWorkspace,
      },
    ],
  };
}

function makeFailedPlaybackRunDetail(workspace: StoryWorkspace): StoryRunDetailResponse {
  const failedRun: StoryRunState = {
    run_id: 'run-failed',
    mode: 'pipeline',
    status: 'failed',
    started_at: '2024-01-01T00:00:00.000Z',
    completed_at: '2024-01-01T00:02:00.000Z',
    published: false,
    stages: [
      {
        name: 'draft',
        status: 'failed',
        started_at: '2024-01-01T00:00:00.000Z',
        completed_at: '2024-01-01T00:02:00.000Z',
        failure_code: 'DRAFT_VALIDATION_ERROR',
        failure_message: 'Scene content cannot be empty',
        details: {
          chapter_number: 2,
          manuscript_preserved: true,
        },
      },
    ],
  };

  const failureArtifact: StoryArtifactHistoryEntry = {
    artifact_id: 'draft-failure-1',
    kind: 'draft_failure',
    version: 1,
    generated_at: '2024-01-01T00:02:00.000Z',
    source_run_id: failedRun.run_id,
    source_stage: 'draft',
    source_provider: 'mock',
    source_model: 'draft-failure-v1',
    parent_artifact_ids: ['blueprint-1', 'outline-1'],
    payload: {
      story_id: workspace.story.id,
      stage_name: 'draft',
      chapter_number: 2,
      failure_code: 'DRAFT_VALIDATION_ERROR',
      failure_message: 'Scene content cannot be empty',
      raw_text: '{"scenes":[{"scene_type":"narrative","title":"Broken scene","content":""}]}',
      raw_payload: {
        scenes: [
          {
            scene_type: 'narrative',
            title: 'Broken scene',
            content: '',
          },
        ],
      },
      normalized_payload: {
        scenes: [
          {
            scene_type: 'narrative',
            title: 'Broken scene',
            content: '',
          },
        ],
      },
      validation_errors: ['Scene content cannot be empty'],
      artifact_id: 'draft-failure-1',
      version: 1,
      generated_at: '2024-01-01T00:02:00.000Z',
      source_run_id: failedRun.run_id,
      source_provider: 'mock',
      source_model: 'draft-failure-v1',
    },
  };

  const playbackWorkspace: StoryWorkspace = {
    ...workspace,
    story: {
      ...workspace.story,
      chapter_count: 1,
      current_chapter_id: workspace.story.chapters[0]?.id ?? workspace.story.current_chapter_id,
      chapters: workspace.story.chapters.slice(0, 1),
    },
    workflow: {
      ...workspace.workflow,
      status: 'draft_failed',
      drafted_chapters: 1,
      current_run_id: failedRun.run_id,
      run_state: failedRun,
    },
    run: failedRun,
    run_history: [failedRun],
    run_events: [
      {
        event_id: 'event-run-started',
        run_id: failedRun.run_id,
        event_type: 'run_started',
        timestamp: '2024-01-01T00:00:00.000Z',
        stage_name: null,
        details: {},
      },
      {
        event_id: 'event-stage-failed',
        run_id: failedRun.run_id,
        event_type: 'stage_failed',
        timestamp: '2024-01-01T00:02:00.000Z',
        stage_name: 'draft',
        details: {
          failure_code: 'DRAFT_VALIDATION_ERROR',
          failure_message: 'Scene content cannot be empty',
          manuscript_preserved: true,
        },
      },
      {
        event_id: 'event-run-failed',
        run_id: failedRun.run_id,
        event_type: 'run_failed',
        timestamp: '2024-01-01T00:02:00.000Z',
        stage_name: 'draft',
        details: {
          failure_code: 'DRAFT_VALIDATION_ERROR',
          failure_message: 'Scene content cannot be empty',
          manuscript_preserved: true,
        },
      },
    ],
    artifact_history: [failureArtifact],
  };

  const failureSnapshot: StoryRunSnapshot = {
    snapshot_id: 'snapshot-failure-1',
    story_id: workspace.story.id,
    run_id: failedRun.run_id,
    snapshot_type: 'run_failed',
    captured_at: '2024-01-01T00:02:00.000Z',
    stage_name: 'draft',
    failed_stage: 'draft',
    failure_code: 'DRAFT_VALIDATION_ERROR',
    failure_message: 'Scene content cannot be empty',
    failure_details: {
      chapter_number: 2,
      manuscript_preserved: true,
      validation_errors: ['Scene content cannot be empty'],
    },
    workspace: playbackWorkspace,
  };

  return {
    operation: 'pipeline',
    run: failedRun,
    events: playbackWorkspace.run_events,
    artifacts: [failureArtifact],
    latest_snapshot: failureSnapshot,
    stage_snapshots: [
      {
        snapshot_id: 'snapshot-stage-1',
        story_id: workspace.story.id,
        run_id: failedRun.run_id,
        snapshot_type: 'stage_completed',
        captured_at: '2024-01-01T00:01:00.000Z',
        stage_name: 'blueprint',
        workspace: playbackWorkspace,
      },
      failureSnapshot,
    ],
    failed_stage: 'draft',
    failure_code: 'DRAFT_VALIDATION_ERROR',
    failure_message: 'Scene content cannot be empty',
    failure_snapshot: failureSnapshot,
    failure_artifacts: [failureArtifact],
    manuscript_preserved: true,
  };
}

describe('StoryWorkbenchPage', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('surfaces relationship and hook debt in the workbench', () => {
    const session: SessionState = {
      kind: 'guest',
      workspaceId: 'workspace-123',
    };
    const workspace = makeStoryWorkspace();
    const mockedUseAuth = vi.mocked(useAuth);
    const mockedUseStoryWorkbench = vi.mocked(useStoryWorkbench);

    mockedUseAuth.mockReturnValue({
      session,
      isLoading: false,
      signInAsGuest: vi.fn(),
      signIn: vi.fn(),
      signOut: vi.fn(),
    });
    mockedUseStoryWorkbench.mockReturnValue({
      stories: [workspace.story],
      activeStoryId: workspace.story.id,
      activeStory: workspace.story,
      workspace,
      currentRun: null,
      runSummaries: [],
      selectedRunId: null,
      selectedRunDetail: null,
      artifact: {
        blueprint: null,
        outline: null,
        review: workspace.review,
        exportPayload: null,
        revisionNotes: workspace.revision_notes,
        pipeline: null,
        run: null,
        lastAction: 'Completed quality review',
      },
      isLoading: false,
      isBusy: false,
      error: null,
      refreshLibrary: vi.fn(),
      selectStory: vi.fn(),
      selectRun: vi.fn(),
      createStory: vi.fn(),
      generateBlueprint: vi.fn(),
      generateOutline: vi.fn(),
      draftStory: vi.fn(),
      reviewStory: vi.fn(),
      reviseStory: vi.fn(),
      exportStory: vi.fn(),
      publishStory: vi.fn(),
      runPipeline: vi.fn(),
      runStoryPipeline: vi.fn(),
    } as UseStoryWorkbenchResult);

    render(<StoryWorkbenchPage />);

    expect(screen.getByTestId('story-relationship-debt-count')).toHaveTextContent('2');
    expect(screen.getByTestId('story-hook-debt-count')).toHaveTextContent('2');
    expect(screen.getByTestId('story-chapter-debt-2')).toHaveTextContent(
      'relationship debt',
    );
    expect(screen.getByTestId('story-chapter-debt-3')).toHaveTextContent('hook debt');
    expect(screen.getByTestId('story-debt-issue-list')).toHaveTextContent(
      'missing_hook_payoff',
    );
  });

  it('keeps mutable workspace metrics separate from run playback', () => {
    const session: SessionState = {
      kind: 'guest',
      workspaceId: 'workspace-123',
    };
    const workspace = makeStoryWorkspace();
    const selectedRunDetail = makePlaybackRunDetail(workspace);
    const mockedUseAuth = vi.mocked(useAuth);
    const mockedUseStoryWorkbench = vi.mocked(useStoryWorkbench);

    mockedUseAuth.mockReturnValue({
      session,
      isLoading: false,
      signInAsGuest: vi.fn(),
      signIn: vi.fn(),
      signOut: vi.fn(),
    });
    mockedUseStoryWorkbench.mockReturnValue({
      stories: [workspace.story],
      activeStoryId: workspace.story.id,
      activeStory: workspace.story,
      workspace,
      currentRun: null,
      runSummaries: [selectedRunDetail.run],
      selectedRunId: selectedRunDetail.run.run_id,
      selectedRunDetail,
      artifact: {
        blueprint: null,
        outline: null,
        review: workspace.review,
        exportPayload: null,
        revisionNotes: workspace.revision_notes,
        pipeline: null,
        run: null,
        lastAction: 'Completed quality review',
      },
      isLoading: false,
      isBusy: false,
      error: null,
      refreshLibrary: vi.fn(),
      selectStory: vi.fn(),
      selectRun: vi.fn(),
      createStory: vi.fn(),
      generateBlueprint: vi.fn(),
      generateOutline: vi.fn(),
      draftStory: vi.fn(),
      reviewStory: vi.fn(),
      reviseStory: vi.fn(),
      exportStory: vi.fn(),
      publishStory: vi.fn(),
      runPipeline: vi.fn(),
      runStoryPipeline: vi.fn(),
    } as UseStoryWorkbenchResult);

    render(<StoryWorkbenchPage />);

    expect(screen.getByTestId('story-review-score')).toHaveTextContent('82');
    expect(screen.getByTestId('story-run-playback')).toHaveTextContent('pipeline / completed');
    expect(screen.getByTestId('story-run-playback')).toHaveTextContent('Quality');
    expect(screen.getByTestId('story-run-playback')).toHaveTextContent('97');
    expect(screen.getByTestId('story-run-playback')).toHaveTextContent('Snapshots');
    expect(screen.getByTestId('story-run-playback')).toHaveTextContent('1');
  });

  it('renders failed run playback details and failure artifacts', () => {
    const session: SessionState = {
      kind: 'guest',
      workspaceId: 'workspace-123',
    };
    const workspace = makeStoryWorkspace();
    const selectedRunDetail = makeFailedPlaybackRunDetail(workspace);
    const mockedUseAuth = vi.mocked(useAuth);
    const mockedUseStoryWorkbench = vi.mocked(useStoryWorkbench);

    mockedUseAuth.mockReturnValue({
      session,
      isLoading: false,
      signInAsGuest: vi.fn(),
      signIn: vi.fn(),
      signOut: vi.fn(),
    });
    mockedUseStoryWorkbench.mockReturnValue({
      stories: [workspace.story],
      activeStoryId: workspace.story.id,
      activeStory: workspace.story,
      workspace,
      currentRun: null,
      runSummaries: [selectedRunDetail.run],
      selectedRunId: selectedRunDetail.run.run_id,
      selectedRunDetail,
      artifact: {
        blueprint: null,
        outline: null,
        review: workspace.review,
        exportPayload: null,
        revisionNotes: workspace.revision_notes,
        pipeline: null,
        run: null,
        lastAction: 'Draft validation failed',
      },
      isLoading: false,
      isBusy: false,
      error: null,
      refreshLibrary: vi.fn(),
      selectStory: vi.fn(),
      selectRun: vi.fn(),
      createStory: vi.fn(),
      generateBlueprint: vi.fn(),
      generateOutline: vi.fn(),
      draftStory: vi.fn(),
      reviewStory: vi.fn(),
      reviseStory: vi.fn(),
      exportStory: vi.fn(),
      publishStory: vi.fn(),
      runPipeline: vi.fn(),
      runStoryPipeline: vi.fn(),
    } as UseStoryWorkbenchResult);

    render(<StoryWorkbenchPage />);

    expect(screen.getByTestId('story-run-playback')).toHaveTextContent('pipeline / failed');
    expect(screen.getByTestId('story-run-failure')).toHaveTextContent('Failed stage: draft');
    expect(screen.getByTestId('story-run-failure')).toHaveTextContent(
      'Scene content cannot be empty',
    );
    expect(screen.getByTestId('story-run-failure')).toHaveTextContent('Manuscript preserved: yes');
    expect(screen.getByTestId('story-run-failure')).toHaveTextContent('Debug artifacts: 1');
    expect(screen.getByTestId('story-run-failure')).toHaveTextContent('draft_failure');
    expect(screen.getByTestId('story-playback-structural-gate')).toHaveTextContent('blocked');
    expect(screen.getByTestId('story-playback-semantic-gate')).toHaveTextContent('blocked');
    expect(screen.getByTestId('story-playback-publish-gate')).toHaveTextContent('blocked');
  });
});
