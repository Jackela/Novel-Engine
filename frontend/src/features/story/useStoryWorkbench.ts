import { useEffect, useRef, useState } from 'react';

import { api } from '@/app/api';
import type {
  StoryBlueprint,
  StoryCreateRequest,
  StoryExportPayload,
  StoryHybridReviewReport,
  StoryListResponse,
  StoryOutline,
  StoryPipelineRequest,
  StoryPipelineResult,
  StoryRunDetailResponse,
  StoryRunsResponse,
  StoryRunState,
  StorySnapshot,
  StorySurfaceView,
  StoryWorkspace,
  StoryWorkflowState,
} from '@/app/types';

export interface StoryWorkbenchArtifact {
  blueprint: StoryBlueprint | null;
  outline: StoryOutline | null;
  review: StoryHybridReviewReport | null;
  exportPayload: StoryExportPayload | null;
  revisionNotes: string[];
  pipeline: StoryPipelineResult | null;
  run: StoryRunState | null;
  lastAction: string | null;
}

export interface UseStoryWorkbenchResult {
  stories: StorySnapshot[];
  activeStoryId: string | null;
  activeStory: StorySnapshot | null;
  workspace: StoryWorkspace | null;
  currentRun: StoryRunState | null;
  runSummaries: StoryRunState[];
  selectedRunId: string | null;
  selectedRunDetail: StoryRunDetailResponse | null;
  artifact: StoryWorkbenchArtifact;
  isLoading: boolean;
  isBusy: boolean;
  error: string | null;
  refreshLibrary: () => Promise<void>;
  selectStory: (storyId: string) => Promise<void>;
  selectRun: (runId: string | null) => Promise<void>;
  createStory: (payload: StoryCreateRequest) => Promise<StorySnapshot>;
  generateBlueprint: () => Promise<void>;
  generateOutline: () => Promise<void>;
  draftStory: (targetChapters?: number | null) => Promise<void>;
  reviewStory: () => Promise<void>;
  reviseStory: () => Promise<void>;
  exportStory: () => Promise<void>;
  publishStory: () => Promise<void>;
  runPipeline: (payload: StoryPipelineRequest) => Promise<StoryPipelineResult>;
  runStoryPipeline: (options?: {
    publish?: boolean;
    targetChapters?: number | null;
  }) => Promise<StoryRunDetailResponse>;
}

interface UseStoryWorkbenchOptions {
  authorId: string;
  preferredStoryId?: string | null;
  preferredRunId?: string | null;
  onSelectionChange?: (selection: {
    storyId: string | null;
    runId: string | null;
    view: StorySurfaceView;
  }) => void;
}

const emptyArtifact: StoryWorkbenchArtifact = {
  blueprint: null,
  outline: null,
  review: null,
  exportPayload: null,
  revisionNotes: [],
  pipeline: null,
  run: null,
  lastAction: null,
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function upsertStory(stories: StorySnapshot[], nextStory: StorySnapshot): StorySnapshot[] {
  const existingIndex = stories.findIndex((story) => story.id === nextStory.id);
  if (existingIndex === -1) {
    return [nextStory, ...stories];
  }

  const nextStories = [...stories];
  nextStories[existingIndex] = nextStory;
  return nextStories;
}

function buildFallbackWorkspace(story: StorySnapshot): StoryWorkspace {
  const rawWorkflow = isRecord(story.metadata.workflow)
    ? (story.metadata.workflow as Partial<StoryWorkflowState>)
    : {};
  const rawMemory = isRecord(story.metadata.story_memory)
    ? (story.metadata.story_memory as Partial<StoryWorkspace['memory']>)
    : {};

  const workflow: StoryWorkflowState = {
    schema_version: rawWorkflow.schema_version ?? 1,
    status: rawWorkflow.status ?? 'created',
    premise: rawWorkflow.premise ?? '',
    tone: rawWorkflow.tone ?? 'commercial web fiction',
    target_chapters: rawWorkflow.target_chapters ?? story.chapter_count ?? 0,
    generation_trace: rawWorkflow.generation_trace ?? [],
    chapter_memory: rawWorkflow.chapter_memory ?? [],
    revision_notes: rawWorkflow.revision_notes ?? [],
    blueprint: rawWorkflow.blueprint ?? null,
    blueprint_generated_at: rawWorkflow.blueprint_generated_at ?? null,
    outline: rawWorkflow.outline ?? null,
    outline_generated_at: rawWorkflow.outline_generated_at ?? null,
    drafted_chapters: rawWorkflow.drafted_chapters ?? story.chapter_count,
    last_structural_review: rawWorkflow.last_structural_review ?? null,
    last_semantic_review: rawWorkflow.last_semantic_review ?? null,
    last_review: rawWorkflow.last_review ?? null,
    last_exported_at: rawWorkflow.last_exported_at ?? null,
    last_updated_at: rawWorkflow.last_updated_at ?? story.updated_at,
    published_at: rawWorkflow.published_at ?? null,
    revision_history: rawWorkflow.revision_history ?? [],
    run_state: rawWorkflow.run_state ?? null,
    current_run_id: rawWorkflow.current_run_id ?? null,
  };

  return {
    story,
    workflow,
    memory: {
      schema_version: rawMemory.schema_version ?? 1,
      premise: rawMemory.premise ?? workflow.premise,
      tone: rawMemory.tone ?? workflow.tone,
      target_chapters: rawMemory.target_chapters ?? workflow.target_chapters,
      themes: rawMemory.themes ?? story.themes,
      chapter_summaries: rawMemory.chapter_summaries ?? workflow.chapter_memory,
      active_characters: rawMemory.active_characters ?? [],
      outline_titles: rawMemory.outline_titles ?? [],
      story_promises: rawMemory.story_promises ?? [],
      timeline_ledger: rawMemory.timeline_ledger ?? [],
      hook_ledger: rawMemory.hook_ledger ?? [],
      promise_ledger: rawMemory.promise_ledger ?? [],
      payoff_beats: rawMemory.payoff_beats ?? [],
      pacing_ledger: rawMemory.pacing_ledger ?? [],
      strand_ledger: rawMemory.strand_ledger ?? [],
      character_states: rawMemory.character_states ?? [],
      relationship_states: rawMemory.relationship_states ?? [],
      world_rules: rawMemory.world_rules ?? [],
      revision_notes: rawMemory.revision_notes ?? workflow.revision_notes,
    },
    blueprint: workflow.blueprint,
    outline: workflow.outline,
    structural_review: workflow.last_structural_review,
    semantic_review: workflow.last_semantic_review,
    hybrid_review: workflow.last_review,
    review: workflow.last_review,
    export: null,
    revision_notes: workflow.revision_notes,
    run: workflow.run_state,
    run_history: [],
    run_events: [],
    artifact_history: [],
  };
}

function resolveWorkspace(workspace: StoryWorkspace | undefined, story: StorySnapshot): StoryWorkspace {
  return workspace ?? buildFallbackWorkspace(story);
}

function deriveArtifactFromWorkspace(workspace: StoryWorkspace): StoryWorkbenchArtifact {
  return {
    blueprint: workspace.blueprint,
    outline: workspace.outline,
    review: workspace.hybrid_review ?? workspace.review,
    exportPayload: workspace.export,
    revisionNotes: workspace.revision_notes,
    pipeline: null,
    run: workspace.run,
    lastAction: workspace.workflow.status
      ? `Workflow status: ${workspace.workflow.status}`
      : null,
  };
}

function formatError(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export function useStoryWorkbench(
  authorIdOrOptions: string | UseStoryWorkbenchOptions,
): UseStoryWorkbenchResult {
  const {
    authorId,
    preferredStoryId,
    preferredRunId,
    onSelectionChange,
  } =
    typeof authorIdOrOptions === 'string'
      ? { authorId: authorIdOrOptions }
      : authorIdOrOptions;
  const [stories, setStories] = useState<StorySnapshot[]>([]);
  const [activeStoryId, setActiveStoryId] = useState<string | null>(null);
  const [workspace, setWorkspace] = useState<StoryWorkspace | null>(null);
  const [currentRun, setCurrentRun] = useState<StoryRunState | null>(null);
  const [runSummaries, setRunSummaries] = useState<StoryRunState[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedRunDetail, setSelectedRunDetail] = useState<StoryRunDetailResponse | null>(
    null,
  );
  const [artifact, setArtifact] = useState<StoryWorkbenchArtifact>(emptyArtifact);
  const [isLoading, setIsLoading] = useState(true);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const activeStoryIdRef = useRef<string | null>(null);
  const selectedRunIdRef = useRef<string | null>(null);
  const preferredStoryIdRef = useRef<string | null>(preferredStoryId ?? null);
  const preferredRunIdRef = useRef<string | null>(preferredRunId ?? null);

  useEffect(() => {
    activeStoryIdRef.current = activeStoryId;
  }, [activeStoryId]);

  useEffect(() => {
    selectedRunIdRef.current = selectedRunId;
  }, [selectedRunId]);

  useEffect(() => {
    preferredStoryIdRef.current = preferredStoryId ?? null;
  }, [preferredStoryId]);

  useEffect(() => {
    preferredRunIdRef.current = preferredRunId ?? null;
  }, [preferredRunId]);

  const notifySelection = (
    storyId: string | null,
    runId: string | null,
    view: StorySurfaceView,
  ) => {
    onSelectionChange?.({
      storyId,
      runId,
      view,
    });
  };

  const syncWorkspace = (
    nextWorkspace: StoryWorkspace,
    patch: Partial<StoryWorkbenchArtifact> = {},
  ) => {
    const baseArtifact = deriveArtifactFromWorkspace(nextWorkspace);

    setStories((current) => upsertStory(current, nextWorkspace.story));
    setActiveStoryId(nextWorkspace.story.id);
    activeStoryIdRef.current = nextWorkspace.story.id;
    setWorkspace(nextWorkspace);
    setArtifact({
      ...baseArtifact,
      ...patch,
      blueprint: patch.blueprint ?? baseArtifact.blueprint,
      outline: patch.outline ?? baseArtifact.outline,
      review: patch.review ?? baseArtifact.review,
      exportPayload: patch.exportPayload ?? baseArtifact.exportPayload,
      revisionNotes: patch.revisionNotes ?? baseArtifact.revisionNotes,
      pipeline: patch.pipeline ?? baseArtifact.pipeline,
      run: patch.run ?? baseArtifact.run,
      lastAction: patch.lastAction ?? baseArtifact.lastAction,
    });
  };

  const clearActiveStory = () => {
    setActiveStoryId(null);
    setWorkspace(null);
    setCurrentRun(null);
    setRunSummaries([]);
    setSelectedRunId(null);
    setSelectedRunDetail(null);
    activeStoryIdRef.current = null;
    selectedRunIdRef.current = null;
    setArtifact(emptyArtifact);
    notifySelection(null, null, 'workspace');
  };

  const syncRunSummaries = (response: StoryRunsResponse) => {
    setCurrentRun(response.current_run);
    setRunSummaries(response.runs);
    return response.runs;
  };

  const clearSelectedRun = () => {
    setSelectedRunId(null);
    setSelectedRunDetail(null);
    selectedRunIdRef.current = null;
    notifySelection(activeStoryIdRef.current, null, 'workspace');
  };

  const syncWorkspaceAndRuns = async (
    nextWorkspace: StoryWorkspace,
    patch: Partial<StoryWorkbenchArtifact> = {},
    options?: {
      selectedRunId?: string | null;
      selectedRunDetail?: StoryRunDetailResponse | null;
    },
  ) => {
    syncWorkspace(nextWorkspace, patch);
    const runsResponse = await api.getStoryRuns(nextWorkspace.story.id);
    const runs = syncRunSummaries(runsResponse);
    const requestedRunId =
      options?.selectedRunId !== undefined
        ? options.selectedRunId
        : selectedRunIdRef.current ?? preferredRunIdRef.current;

    if (!requestedRunId) {
      if (options?.selectedRunDetail === null) {
        clearSelectedRun();
      } else {
        notifySelection(nextWorkspace.story.id, null, 'workspace');
      }
      return;
    }

    if (!runs.some((run) => run.run_id === requestedRunId)) {
      clearSelectedRun();
      return;
    }

    const runDetail =
      options?.selectedRunDetail && options.selectedRunDetail.run.run_id === requestedRunId
        ? options.selectedRunDetail
        : await api.getStoryRun(nextWorkspace.story.id, requestedRunId);

    setSelectedRunId(requestedRunId);
    selectedRunIdRef.current = requestedRunId;
    setSelectedRunDetail(runDetail);
    notifySelection(nextWorkspace.story.id, requestedRunId, 'playback');
  };

  const refreshLibrary = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response: StoryListResponse = await api.listStories(authorId);
      setStories(response.stories);

      if (response.stories.length === 0) {
        clearActiveStory();
        return;
      }

      const selectedStory =
        response.stories.find(
          (story) =>
            story.id === preferredStoryIdRef.current ||
            story.id === activeStoryIdRef.current,
        ) ??
        response.stories[0];
      const workspaceResponse = await api.getStoryWorkspace(selectedStory.id);
      await syncWorkspaceAndRuns(
        resolveWorkspace(workspaceResponse.workspace, selectedStory),
      );
    } catch (nextError) {
      setError(formatError(nextError, 'Unable to load story library.'));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void refreshLibrary();
    // The refresh function is intentionally re-created for the current author.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authorId]);

  const performAction = async <T,>(
    action: () => Promise<T>,
    onSuccess: (result: T) => Promise<void> | void,
    fallbackError: string,
  ) => {
    setIsBusy(true);
    setError(null);

    try {
      const result = await action();
      await onSuccess(result);
      return result;
    } catch (nextError) {
      setError(formatError(nextError, fallbackError));
      throw nextError;
    } finally {
      setIsBusy(false);
    }
  };

  const ensureActiveStoryId = (): string => {
    if (!activeStoryIdRef.current) {
      throw new Error('Select a story before running a workflow action.');
    }

    return activeStoryIdRef.current;
  };

  const createStory = async (payload: StoryCreateRequest) => {
    const result = await performAction(
      async () =>
        api.createStory({
          ...payload,
          author_id: payload.author_id ?? authorId,
        }),
      async (result) => {
        const workspaceResponse = await api.getStoryWorkspace(result.story.id);
        await syncWorkspaceAndRuns(workspaceResponse.workspace, {
          lastAction: 'Created draft manuscript',
        }, {
          selectedRunId: null,
          selectedRunDetail: null,
        });
      },
      'Unable to create the story.',
    );
    return result.story;
  };

  const generateBlueprint = async () => {
    await performAction(
      async () => api.generateBlueprint(ensureActiveStoryId()),
      async (result) => {
        await syncWorkspaceAndRuns(resolveWorkspace(result.workspace, result.story), {
          blueprint: result.blueprint,
          lastAction: 'Generated blueprint',
        });
      },
      'Unable to generate the blueprint.',
    );
  };

  const generateOutline = async () => {
    await performAction(
      async () => api.generateOutline(ensureActiveStoryId()),
      async (result) => {
        await syncWorkspaceAndRuns(resolveWorkspace(result.workspace, result.story), {
          outline: result.outline,
          lastAction: 'Generated outline',
        });
      },
      'Unable to generate the outline.',
    );
  };

  const draftStory = async (targetChapters?: number | null) => {
    await performAction(
      async () => api.draftStory(ensureActiveStoryId(), targetChapters),
      async (result) => {
        await syncWorkspaceAndRuns(resolveWorkspace(result.workspace, result.story), {
          lastAction: result.skipped
            ? 'Draft already matched the configured target'
            : `Drafted ${result.drafted_chapters} chapters`,
        });
      },
      'Unable to draft the story.',
    );
  };

  const reviewStory = async () => {
    await performAction(
      async () => api.reviewStory(ensureActiveStoryId()),
      async (result) => {
        await syncWorkspaceAndRuns(resolveWorkspace(result.workspace, result.story), {
          review: result.report,
          lastAction: 'Completed quality review',
        });
      },
      'Unable to review the story.',
    );
  };

  const reviseStory = async () => {
    await performAction(
      async () => api.reviseStory(ensureActiveStoryId()),
      async (result) => {
        await syncWorkspaceAndRuns(resolveWorkspace(result.workspace, result.story), {
          review: result.report,
          revisionNotes: result.revision_notes,
          lastAction: 'Applied revision pass',
        });
      },
      'Unable to revise the story.',
    );
  };

  const exportStory = async () => {
    await performAction(
      async () => api.exportStory(ensureActiveStoryId()),
      async (result) => {
        await syncWorkspaceAndRuns(resolveWorkspace(result.workspace, result.story), {
          exportPayload: result.export,
          lastAction: 'Exported manuscript bundle',
        });
      },
      'Unable to export the story.',
    );
  };

  const publishStory = async () => {
    await performAction(
      async () => api.publishStory(ensureActiveStoryId()),
      async (result) => {
        await syncWorkspaceAndRuns(resolveWorkspace(result.workspace, result.story), {
          review: result.report,
          lastAction: 'Published story',
        });
      },
      'Unable to publish the story.',
    );
  };

  const selectStory = async (storyId: string) => {
    await performAction(
      async () => api.getStoryWorkspace(storyId),
      async (result) => {
        clearSelectedRun();
        await syncWorkspaceAndRuns(result.workspace, {}, { selectedRunId: null });
      },
      'Unable to load the selected story.',
    );
  };

  const selectRun = async (runId: string | null) => {
    if (!runId) {
      clearSelectedRun();
      return;
    }

    await performAction(
      async () => api.getStoryRun(ensureActiveStoryId(), runId),
      (result) => {
        setSelectedRunId(result.run.run_id);
        selectedRunIdRef.current = result.run.run_id;
        setSelectedRunDetail(result);
      },
      'Unable to load run playback.',
    );
  };

  const runPipeline = async (payload: StoryPipelineRequest) => {
    const result = await performAction(
      async () =>
        api.runPipeline({
          ...payload,
          author_id: payload.author_id ?? authorId,
        }),
      async (result) => {
        clearSelectedRun();
        await syncWorkspaceAndRuns(resolveWorkspace(result.workspace, result.story), {
          blueprint: result.blueprint,
          outline: result.outline,
          review: result.final_review,
          exportPayload: result.export,
          revisionNotes: result.revision_notes,
          pipeline: result,
          lastAction: result.published
            ? 'Completed pipeline and published story'
            : 'Completed pipeline',
        });
      },
      'Unable to run the full pipeline.',
    );
    return result;
  };

  const runStoryPipeline = async (options?: {
    publish?: boolean;
    targetChapters?: number | null;
  }) => {
    const storyId = ensureActiveStoryId();
    const result = await performAction(
      async () =>
        api.createStoryRun(storyId, {
          operation: 'pipeline',
          publish: options?.publish ?? false,
          target_chapters: options?.targetChapters ?? null,
        }),
      async (result) => {
        const workspaceResponse = await api.getStoryWorkspace(storyId);
        await syncWorkspaceAndRuns(workspaceResponse.workspace, {
          review: workspaceResponse.workspace.review,
          exportPayload: workspaceResponse.workspace.export,
          run: result.run,
          lastAction: result.run.published
            ? 'Re-ran pipeline and published story'
            : 'Re-ran pipeline for current story',
        }, {
          selectedRunId: result.run.run_id,
          selectedRunDetail: result,
        });
      },
      'Unable to run the pipeline for the current story.',
    );
    return result;
  };

  return {
    stories,
    activeStoryId,
    activeStory: workspace?.story ?? null,
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
  };
}
