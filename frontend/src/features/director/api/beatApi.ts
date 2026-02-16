/**
 * Beat API Hooks using TanStack Query
 *
 * Why: Provides type-safe access to Beat CRUD endpoints with optimistic
 * updates and cache invalidation. Beats are atomic narrative units within
 * scenes used for granular story editing in Director Mode.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  BeatResponseSchema,
  BeatListResponseSchema,
  BeatCreateRequestSchema,
  type BeatResponse,
  type BeatListResponse,
  type BeatCreateRequest,
  type BeatUpdateRequest,
} from '@/types/schemas';

/**
 * Query key factory for beats.
 * Why: Centralizes key creation for consistent cache management.
 */
const beatKeys = {
  all: ['beats'] as const,
  list: (sceneId: string) => [...beatKeys.all, 'list', sceneId] as const,
  detail: (sceneId: string, beatId: string) =>
    [...beatKeys.all, 'detail', sceneId, beatId] as const,
};

// ============ Raw API Functions ============

/**
 * List all beats in a scene.
 */
async function listBeats(sceneId: string): Promise<BeatListResponse> {
  const data = await api.get<unknown>(`/structure/scenes/${sceneId}/beats`);
  return BeatListResponseSchema.parse(data);
}

/**
 * Get a single beat by ID.
 */
async function getBeat(sceneId: string, beatId: string): Promise<BeatResponse> {
  const data = await api.get<unknown>(`/structure/scenes/${sceneId}/beats/${beatId}`);
  return BeatResponseSchema.parse(data);
}

/**
 * Create a new beat in a scene.
 */
async function createBeat(
  sceneId: string,
  input: BeatCreateRequest
): Promise<BeatResponse> {
  const payload = BeatCreateRequestSchema.parse(input);
  const data = await api.post<unknown>(`/structure/scenes/${sceneId}/beats`, payload);
  return BeatResponseSchema.parse(data);
}

/**
 * Update a beat.
 */
async function updateBeat(
  sceneId: string,
  beatId: string,
  updates: BeatUpdateRequest
): Promise<BeatResponse> {
  const data = await api.patch<unknown>(
    `/structure/scenes/${sceneId}/beats/${beatId}`,
    updates
  );
  return BeatResponseSchema.parse(data);
}

/**
 * Delete a beat.
 */
async function deleteBeat(sceneId: string, beatId: string): Promise<void> {
  await api.delete<unknown>(`/structure/scenes/${sceneId}/beats/${beatId}`);
}

/**
 * Reorder beats within a scene.
 */
async function reorderBeats(
  sceneId: string,
  beatIds: string[]
): Promise<BeatListResponse> {
  const data = await api.post<unknown>(`/structure/scenes/${sceneId}/beats/reorder`, {
    beat_ids: beatIds,
  });
  return BeatListResponseSchema.parse(data);
}

// ============ TanStack Query Hooks ============

/**
 * Hook to fetch all beats in a scene.
 */
export function useBeats(sceneId: string | undefined) {
  return useQuery({
    queryKey: beatKeys.list(sceneId ?? ''),
    queryFn: () => listBeats(sceneId!),
    enabled: !!sceneId,
  });
}

/**
 * Hook to fetch a single beat.
 */
export function useBeat(sceneId: string | undefined, beatId: string | undefined) {
  return useQuery({
    queryKey: beatKeys.detail(sceneId ?? '', beatId ?? ''),
    queryFn: () => getBeat(sceneId!, beatId!),
    enabled: !!sceneId && !!beatId,
  });
}

/**
 * Hook to create a new beat.
 *
 * Why: Provides optimistic updates for immediate UI feedback.
 */
export function useCreateBeat() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sceneId, input }: { sceneId: string; input: BeatCreateRequest }) =>
      createBeat(sceneId, input),
    onSuccess: (data) => {
      // Invalidate beats list for the scene
      queryClient.invalidateQueries({ queryKey: beatKeys.list(data.scene_id) });
    },
  });
}

/**
 * Hook to update a beat.
 */
export function useUpdateBeat() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      sceneId,
      beatId,
      updates,
    }: {
      sceneId: string;
      beatId: string;
      updates: BeatUpdateRequest;
    }) => updateBeat(sceneId, beatId, updates),
    onSuccess: (data) => {
      // Update cache with new data
      queryClient.setQueryData(beatKeys.detail(data.scene_id, data.id), data);
      queryClient.invalidateQueries({ queryKey: beatKeys.list(data.scene_id) });
    },
  });
}

/**
 * Hook to delete a beat.
 */
export function useDeleteBeat() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sceneId, beatId }: { sceneId: string; beatId: string }) =>
      deleteBeat(sceneId, beatId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: beatKeys.list(variables.sceneId) });
    },
  });
}

/**
 * Hook to reorder beats within a scene.
 *
 * Why: Supports drag-and-drop reordering in the UI with optimistic updates.
 */
export function useReorderBeats() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sceneId, beatIds }: { sceneId: string; beatIds: string[] }) =>
      reorderBeats(sceneId, beatIds),
    // Optimistic update for immediate visual feedback
    onMutate: async ({ sceneId, beatIds }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: beatKeys.list(sceneId) });

      // Snapshot the previous value
      const previousBeats = queryClient.getQueryData<BeatListResponse>(
        beatKeys.list(sceneId)
      );

      // Optimistically update with new order
      if (previousBeats) {
        const reorderedBeats = beatIds
          .map((id, index) => {
            const beat = previousBeats.beats.find((b) => b.id === id);
            return beat ? { ...beat, order_index: index } : null;
          })
          .filter((b): b is BeatResponse => b !== null);

        queryClient.setQueryData<BeatListResponse>(beatKeys.list(sceneId), {
          ...previousBeats,
          beats: reorderedBeats,
        });
      }

      return { previousBeats };
    },
    // If mutation fails, roll back to previous value
    onError: (_, variables, context) => {
      if (context?.previousBeats) {
        queryClient.setQueryData(
          beatKeys.list(variables.sceneId),
          context.previousBeats
        );
      }
    },
    // Always refetch after error or success
    onSettled: (_, __, variables) => {
      queryClient.invalidateQueries({ queryKey: beatKeys.list(variables.sceneId) });
    },
  });
}

// Export raw functions for non-hook usage
export { listBeats, getBeat, createBeat, updateBeat, deleteBeat, reorderBeats };
