import { useEffect, useRef, useState } from 'react';

import { api } from '@/app/api';
import type {
  StoryBlueprint,
  StoryCreateRequest,
  StoryExportPayload,
  StoryListResponse,
  StoryOutline,
  StoryPipelineRequest,
  StoryPipelineResult,
  StoryReviewReport,
  StorySnapshot,
  StoryWorkflowState,
} from '@/app/types';

export interface StoryWorkbenchArtifact {
  blueprint: StoryBlueprint | null;
  outline: StoryOutline | null;
  review: StoryReviewReport | null;
  exportPayload: StoryExportPayload | null;
  revisionNotes: string[];
  pipeline: StoryPipelineResult | null;
  lastAction: string | null;
}

export interface UseStoryWorkbenchResult {
  stories: StorySnapshot[];
  activeStoryId: string | null;
  activeStory: StorySnapshot | null;
  artifact: StoryWorkbenchArtifact;
  isLoading: boolean;
  isBusy: boolean;
  error: string | null;
  refreshLibrary: () => Promise<void>;
  selectStory: (storyId: string) => Promise<void>;
  createStory: (payload: StoryCreateRequest) => Promise<StorySnapshot>;
  generateBlueprint: () => Promise<void>;
  generateOutline: () => Promise<void>;
  draftStory: (targetChapters?: number | null) => Promise<void>;
  reviewStory: () => Promise<void>;
  reviseStory: () => Promise<void>;
  exportStory: () => Promise<void>;
  publishStory: () => Promise<void>;
  runPipeline: (payload: StoryPipelineRequest) => Promise<StoryPipelineResult>;
}

const emptyArtifact: StoryWorkbenchArtifact = {
  blueprint: null,
  outline: null,
  review: null,
  exportPayload: null,
  revisionNotes: [],
  pipeline: null,
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

function deriveArtifactFromStory(story: StorySnapshot): StoryWorkbenchArtifact {
  const workflow = isRecord(story.metadata.workflow)
    ? (story.metadata.workflow as StoryWorkflowState)
    : null;

  return {
    blueprint: workflow?.blueprint ?? null,
    outline: workflow?.outline ?? null,
    review: workflow?.last_review ?? null,
    exportPayload: null,
    revisionNotes: workflow?.revision_notes ?? [],
    pipeline: null,
    lastAction: workflow?.status ? `Workflow status: ${workflow.status}` : null,
  };
}

function formatError(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export function useStoryWorkbench(authorId: string): UseStoryWorkbenchResult {
  const [stories, setStories] = useState<StorySnapshot[]>([]);
  const [activeStoryId, setActiveStoryId] = useState<string | null>(null);
  const [activeStory, setActiveStory] = useState<StorySnapshot | null>(null);
  const [artifact, setArtifact] = useState<StoryWorkbenchArtifact>(emptyArtifact);
  const [isLoading, setIsLoading] = useState(true);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const activeStoryIdRef = useRef<string | null>(null);

  useEffect(() => {
    activeStoryIdRef.current = activeStoryId;
  }, [activeStoryId]);

  const syncStory = (
    nextStory: StorySnapshot,
    patch: Partial<StoryWorkbenchArtifact> = {},
  ) => {
    const baseArtifact = deriveArtifactFromStory(nextStory);

    setStories((current) => upsertStory(current, nextStory));
    setActiveStory(nextStory);
    setActiveStoryId(nextStory.id);
    activeStoryIdRef.current = nextStory.id;
    setArtifact({
      ...baseArtifact,
      ...patch,
      blueprint: patch.blueprint ?? baseArtifact.blueprint,
      outline: patch.outline ?? baseArtifact.outline,
      review: patch.review ?? baseArtifact.review,
      exportPayload: patch.exportPayload ?? baseArtifact.exportPayload,
      revisionNotes: patch.revisionNotes ?? baseArtifact.revisionNotes,
      pipeline: patch.pipeline ?? baseArtifact.pipeline,
      lastAction: patch.lastAction ?? baseArtifact.lastAction,
    });
  };

  const clearActiveStory = () => {
    setActiveStoryId(null);
    setActiveStory(null);
    activeStoryIdRef.current = null;
    setArtifact(emptyArtifact);
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
        response.stories.find((story) => story.id === activeStoryIdRef.current) ??
        response.stories[0];
      syncStory(selectedStory);
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
    onSuccess: (result: T) => void,
    fallbackError: string,
  ) => {
    setIsBusy(true);
    setError(null);

    try {
      const result = await action();
      onSuccess(result);
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
      (result) => {
        syncStory(result.story, {
          lastAction: 'Created draft manuscript',
        });
      },
      'Unable to create the story.',
    );
    return result.story;
  };

  const generateBlueprint = async () => {
    await performAction(
      async () => api.generateBlueprint(ensureActiveStoryId()),
      (result) => {
        syncStory(result.story, {
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
      (result) => {
        syncStory(result.story, {
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
      (result) => {
        syncStory(result.story, {
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
      (result) => {
        syncStory(result.story, {
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
      (result) => {
        syncStory(result.story, {
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
      (result) => {
        syncStory(result.story, {
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
      (result) => {
        syncStory(result.story, {
          review: result.report,
          lastAction: 'Published story',
        });
      },
      'Unable to publish the story.',
    );
  };

  const selectStory = async (storyId: string) => {
    await performAction(
      async () => api.getStory(storyId),
      (result) => {
        syncStory(result.story);
      },
      'Unable to load the selected story.',
    );
  };

  const runPipeline = async (payload: StoryPipelineRequest) => {
    const result = await performAction(
      async () =>
        api.runPipeline({
          ...payload,
          author_id: payload.author_id ?? authorId,
        }),
      (result) => {
        syncStory(result.story, {
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

  return {
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
  };
}
