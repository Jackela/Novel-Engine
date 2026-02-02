/**
 * useStoryStructure - Hook for loading and managing story structure data.
 *
 * Why: Provides a centralized hook for fetching chapters and scenes from the
 * backend Structure API, transforming them into the format expected by the
 * NarrativeSidebar component. This hook handles loading states, error handling,
 * and automatic refresh capabilities.
 */
import { useState, useCallback, useEffect } from 'react';
import {
  listStories,
  listChapters,
  listScenes,
  createStory,
  createChapter,
  createScene,
} from '@/lib/api';
import type {
  StoryResponse,
  ChapterResponse,
  SceneResponse,
  StoryCreateRequest,
  ChapterCreateRequest,
  SceneCreateRequest,
} from '@/types/schemas';
import type {
  OutlinerChapter,
  OutlinerScene,
} from '@/components/narrative/NarrativeSidebar';

/**
 * State for story structure data.
 */
interface StoryStructureState {
  /** The currently selected story */
  story: StoryResponse | null;
  /** Chapters with their scenes in outliner format */
  chapters: OutlinerChapter[];
  /** Loading state */
  isLoading: boolean;
  /** Error message if loading failed */
  error: string | null;
  /** All available stories for selection */
  stories: StoryResponse[];
}

/**
 * Actions returned by the hook for modifying story structure.
 */
interface StoryStructureActions {
  /** Load all stories and select the first one */
  loadStories: () => Promise<void>;
  /** Select a specific story and load its structure */
  selectStory: (storyId: string) => Promise<void>;
  /** Refresh the current story's structure */
  refresh: () => Promise<void>;
  /** Create a new story and select it */
  addStory: (input: StoryCreateRequest) => Promise<StoryResponse>;
  /** Create a new chapter in the current story */
  addChapter: (input: ChapterCreateRequest) => Promise<ChapterResponse>;
  /** Create a new scene in a chapter */
  addScene: (chapterId: string, input: SceneCreateRequest) => Promise<SceneResponse>;
}

/**
 * Transform backend responses into OutlinerChapter format.
 *
 * Why: The NarrativeSidebar expects a specific format with nested scenes,
 * while the backend returns chapters and scenes separately. This transformation
 * combines the data into the expected tree structure.
 */
function transformToOutlinerFormat(
  chapters: ChapterResponse[],
  scenesByChapter: Map<string, SceneResponse[]>
): OutlinerChapter[] {
  return chapters.map((chapter) => {
    const scenes = scenesByChapter.get(chapter.id) || [];
    return {
      id: chapter.id,
      story_id: chapter.story_id,
      title: chapter.title,
      order_index: chapter.order_index,
      status: chapter.status,
      scenes: scenes.map(
        (scene): OutlinerScene => ({
          id: scene.id,
          chapter_id: scene.chapter_id,
          title: scene.title,
          order_index: scene.order_index,
          status: scene.status,
        })
      ),
    };
  });
}

/**
 * Hook for managing story structure data.
 *
 * Why: Encapsulates all the complexity of loading chapters and scenes from
 * multiple API calls, handling loading/error states, and providing a clean
 * interface for the UI components.
 *
 * @param initialStoryId - Optional story ID to load on mount
 * @returns State and actions for managing story structure
 */
export function useStoryStructure(
  initialStoryId?: string
): StoryStructureState & StoryStructureActions {
  const [state, setState] = useState<StoryStructureState>({
    story: null,
    chapters: [],
    isLoading: false,
    error: null,
    stories: [],
  });

  /**
   * Load a story's full structure (chapters with scenes).
   */
  const loadStoryStructure = useCallback(
    async (storyId: string, story: StoryResponse): Promise<void> => {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));

      try {
        // Fetch chapters
        const chaptersResponse = await listChapters(storyId);
        const chapters = chaptersResponse.chapters;

        // Fetch scenes for each chapter in parallel
        const scenesPromises = chapters.map((chapter) =>
          listScenes(storyId, chapter.id).then((res) => ({
            chapterId: chapter.id,
            scenes: res.scenes,
          }))
        );

        const scenesResults = await Promise.all(scenesPromises);

        // Build scenes map
        const scenesByChapter = new Map<string, SceneResponse[]>();
        for (const result of scenesResults) {
          scenesByChapter.set(result.chapterId, result.scenes);
        }

        // Transform to outliner format
        const outlinerChapters = transformToOutlinerFormat(chapters, scenesByChapter);

        setState((prev) => ({
          ...prev,
          story,
          chapters: outlinerChapters,
          isLoading: false,
          error: null,
        }));
      } catch (error) {
        const message =
          error instanceof Error ? error.message : 'Failed to load story structure';
        setState((prev) => ({
          ...prev,
          isLoading: false,
          error: message,
        }));
      }
    },
    []
  );

  /**
   * Load all stories and optionally select one.
   */
  const loadStories = useCallback(async (): Promise<void> => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await listStories();
      const stories = response.stories;

      setState((prev) => ({ ...prev, stories, isLoading: false }));

      // Auto-select first story if available and none selected
      const firstStory = stories[0];
      if (firstStory && !state.story) {
        await loadStoryStructure(firstStory.id, firstStory);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to load stories';
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
    }
  }, [state.story, loadStoryStructure]);

  /**
   * Select a specific story and load its structure.
   */
  const selectStory = useCallback(
    async (storyId: string): Promise<void> => {
      const foundStory = state.stories.find((s) => s.id === storyId);
      if (foundStory) {
        await loadStoryStructure(storyId, foundStory);
      }
    },
    [state.stories, loadStoryStructure]
  );

  /**
   * Refresh the current story's structure.
   */
  const refresh = useCallback(async (): Promise<void> => {
    if (state.story) {
      await loadStoryStructure(state.story.id, state.story);
    }
  }, [state.story, loadStoryStructure]);

  /**
   * Create a new story and select it.
   */
  const addStory = useCallback(
    async (input: StoryCreateRequest): Promise<StoryResponse> => {
      const story = await createStory(input);
      setState((prev) => ({
        ...prev,
        stories: [...prev.stories, story],
        story,
        chapters: [],
      }));
      return story;
    },
    []
  );

  /**
   * Create a new chapter in the current story.
   */
  const addChapter = useCallback(
    async (input: ChapterCreateRequest): Promise<ChapterResponse> => {
      if (!state.story) {
        throw new Error('No story selected');
      }
      const chapter = await createChapter(state.story.id, input);

      // Refresh to get updated structure
      await refresh();

      return chapter;
    },
    [state.story, refresh]
  );

  /**
   * Create a new scene in a chapter.
   */
  const addScene = useCallback(
    async (chapterId: string, input: SceneCreateRequest): Promise<SceneResponse> => {
      if (!state.story) {
        throw new Error('No story selected');
      }
      const scene = await createScene(state.story.id, chapterId, input);

      // Refresh to get updated structure
      await refresh();

      return scene;
    },
    [state.story, refresh]
  );

  // Load initial story if provided
  useEffect(() => {
    if (initialStoryId) {
      // Find story in list or load it
      const foundStory = state.stories.find((s) => s.id === initialStoryId);
      if (foundStory) {
        loadStoryStructure(initialStoryId, foundStory);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialStoryId]);

  return {
    ...state,
    loadStories,
    selectStory,
    refresh,
    addStory,
    addChapter,
    addScene,
  };
}

export default useStoryStructure;
