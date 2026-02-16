/**
 * Scene API Hooks using TanStack Query for Director Mode
 *
 * Why: Provides type-safe access to Scene CRUD endpoints with optimistic
 * updates and cache invalidation. Scenes are organized by story_phase for
 * the Chapter Board View (Kanban-style organization).
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  SceneResponseSchema,
  SceneListResponseSchema,
  type SceneResponse,
  type SceneListResponse,
  type StoryPhase,
} from '@/types/schemas';

/**
 * Query key factory for scenes.
 * Why: Centralizes key creation for consistent cache management.
 */
export const sceneKeys = {
  all: ['scenes'] as const,
  list: (storyId: string, chapterId: string) =>
    [...sceneKeys.all, 'list', storyId, chapterId] as const,
  detail: (storyId: string, chapterId: string, sceneId: string) =>
    [...sceneKeys.all, 'detail', storyId, chapterId, sceneId] as const,
};

// ============ Raw API Functions ============

/**
 * List all scenes in a chapter.
 */
async function listScenes(
  storyId: string,
  chapterId: string
): Promise<SceneListResponse> {
  const data = await api.get<unknown>(
    `/structure/stories/${storyId}/chapters/${chapterId}/scenes`
  );
  return SceneListResponseSchema.parse(data);
}

/**
 * Get a single scene by ID.
 */
async function getScene(
  storyId: string,
  chapterId: string,
  sceneId: string
): Promise<SceneResponse> {
  const data = await api.get<unknown>(
    `/structure/stories/${storyId}/chapters/${chapterId}/scenes/${sceneId}`
  );
  return SceneResponseSchema.parse(data);
}

/**
 * Update a scene's story_phase.
 *
 * Why: Primary method for Chapter Board View drag-and-drop between columns.
 */
async function updateScenePhase(
  storyId: string,
  chapterId: string,
  sceneId: string,
  story_phase: StoryPhase
): Promise<SceneResponse> {
  const data = await api.patch<unknown>(
    `/structure/stories/${storyId}/chapters/${chapterId}/scenes/${sceneId}`,
    { story_phase }
  );
  return SceneResponseSchema.parse(data);
}

// ============ TanStack Query Hooks ============

/**
 * Hook to fetch all scenes in a chapter.
 */
export function useScenes(storyId: string | undefined, chapterId: string | undefined) {
  return useQuery({
    queryKey: sceneKeys.list(storyId ?? '', chapterId ?? ''),
    queryFn: () => listScenes(storyId!, chapterId!),
    enabled: !!storyId && !!chapterId,
  });
}

/**
 * Hook to fetch a single scene.
 */
export function useScene(
  storyId: string | undefined,
  chapterId: string | undefined,
  sceneId: string | undefined
) {
  return useQuery({
    queryKey: sceneKeys.detail(storyId ?? '', chapterId ?? '', sceneId ?? ''),
    queryFn: () => getScene(storyId!, chapterId!, sceneId!),
    enabled: !!storyId && !!chapterId && !!sceneId,
  });
}

/**
 * Hook to update a scene's story_phase.
 *
 * Why: Supports drag-and-drop between Kanban columns in Chapter Board View.
 */
export function useUpdateScenePhase() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      storyId,
      chapterId,
      sceneId,
      storyPhase,
    }: {
      storyId: string;
      chapterId: string;
      sceneId: string;
      storyPhase: StoryPhase;
    }) => updateScenePhase(storyId, chapterId, sceneId, storyPhase),
    onSuccess: (data) => {
      // Update cache with new data
      queryClient.setQueryData(
        sceneKeys.detail(
          // Extract IDs from data since story/chapter IDs aren't directly in response
          '', // We'll invalidate by list instead
          '',
          data.id
        ),
        data
      );
      // Invalidate the list query
      queryClient.invalidateQueries({
        queryKey: sceneKeys.all,
      });
    },
  });
}

// Export raw functions for non-hook usage
export { listScenes, getScene, updateScenePhase };
