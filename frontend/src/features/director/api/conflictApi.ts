/**
 * Conflict API Hooks using TanStack Query
 *
 * Why: Provides type-safe access to Conflict CRUD endpoints with optimistic
 * updates and cache invalidation. Conflicts are dramatic tension drivers
 * within scenes used for stakes tracking in Director Mode.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  ConflictResponseSchema,
  ConflictListResponseSchema,
  ConflictCreateRequestSchema,
  type ConflictResponse,
  type ConflictListResponse,
  type ConflictCreateRequest,
  type ConflictUpdateRequest,
} from '@/types/schemas';

/**
 * Query key factory for conflicts.
 * Why: Centralizes key creation for consistent cache management.
 */
export const conflictKeys = {
  all: ['conflicts'] as const,
  list: (sceneId: string) => [...conflictKeys.all, 'list', sceneId] as const,
  detail: (sceneId: string, conflictId: string) =>
    [...conflictKeys.all, 'detail', sceneId, conflictId] as const,
};

// ============ Raw API Functions ============

/**
 * List all conflicts in a scene.
 */
async function listConflicts(sceneId: string): Promise<ConflictListResponse> {
  const data = await api.get<unknown>(`/structure/scenes/${sceneId}/conflicts`);
  return ConflictListResponseSchema.parse(data);
}

/**
 * Get a single conflict by ID.
 */
async function getConflict(sceneId: string, conflictId: string): Promise<ConflictResponse> {
  const data = await api.get<unknown>(`/structure/scenes/${sceneId}/conflicts/${conflictId}`);
  return ConflictResponseSchema.parse(data);
}

/**
 * Create a new conflict in a scene.
 */
async function createConflict(
  sceneId: string,
  input: ConflictCreateRequest
): Promise<ConflictResponse> {
  const payload = ConflictCreateRequestSchema.parse(input);
  const data = await api.post<unknown>(`/structure/scenes/${sceneId}/conflicts`, payload);
  return ConflictResponseSchema.parse(data);
}

/**
 * Update a conflict.
 */
async function updateConflict(
  sceneId: string,
  conflictId: string,
  updates: ConflictUpdateRequest
): Promise<ConflictResponse> {
  const data = await api.patch<unknown>(
    `/structure/scenes/${sceneId}/conflicts/${conflictId}`,
    updates
  );
  return ConflictResponseSchema.parse(data);
}

/**
 * Delete a conflict.
 */
async function deleteConflict(sceneId: string, conflictId: string): Promise<void> {
  await api.delete<unknown>(`/structure/scenes/${sceneId}/conflicts/${conflictId}`);
}

// ============ TanStack Query Hooks ============

/**
 * Hook to fetch all conflicts in a scene.
 */
export function useConflicts(sceneId: string | undefined) {
  return useQuery({
    queryKey: conflictKeys.list(sceneId ?? ''),
    queryFn: () => listConflicts(sceneId!),
    enabled: !!sceneId,
  });
}

/**
 * Hook to fetch a single conflict.
 */
export function useConflict(sceneId: string | undefined, conflictId: string | undefined) {
  return useQuery({
    queryKey: conflictKeys.detail(sceneId ?? '', conflictId ?? ''),
    queryFn: () => getConflict(sceneId!, conflictId!),
    enabled: !!sceneId && !!conflictId,
  });
}

/**
 * Hook to create a new conflict.
 *
 * Why: Provides optimistic updates for immediate UI feedback.
 */
export function useCreateConflict() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sceneId, input }: { sceneId: string; input: ConflictCreateRequest }) =>
      createConflict(sceneId, input),
    onSuccess: (data) => {
      // Invalidate conflicts list for the scene
      queryClient.invalidateQueries({ queryKey: conflictKeys.list(data.scene_id) });
    },
  });
}

/**
 * Hook to update a conflict.
 */
export function useUpdateConflict() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      sceneId,
      conflictId,
      updates,
    }: {
      sceneId: string;
      conflictId: string;
      updates: ConflictUpdateRequest;
    }) => updateConflict(sceneId, conflictId, updates),
    onSuccess: (data) => {
      // Update cache with new data
      queryClient.setQueryData(conflictKeys.detail(data.scene_id, data.id), data);
      queryClient.invalidateQueries({ queryKey: conflictKeys.list(data.scene_id) });
    },
  });
}

/**
 * Hook to delete a conflict.
 */
export function useDeleteConflict() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sceneId, conflictId }: { sceneId: string; conflictId: string }) =>
      deleteConflict(sceneId, conflictId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: conflictKeys.list(variables.sceneId) });
    },
  });
}

// Export raw functions for non-hook usage
export { listConflicts, getConflict, createConflict, updateConflict, deleteConflict };
