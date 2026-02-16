/**
 * Smart Tags React Query Hooks
 *
 * BRAIN-038-05: Manual Tag Override
 * Provides React Query hooks for smart tags with optimistic updates
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
} from '@tanstack/react-query';
import { toast } from 'sonner';
import { smartTagsApi, type SmartTagsResponse } from './smartTagsApi';

// === Query Keys ===

export const smartTagsQueryKeys = {
  all: ['smart-tags'] as const,
  lore: (entryId: string) => ['smart-tags', 'lore', entryId] as const,
  scene: (storyId: string, chapterId: string, sceneId: string) =>
    ['smart-tags', 'scene', storyId, chapterId, sceneId] as const,
} as const;

// === Query Hooks ===

/**
 * Fetch smart tags for a lore entry
 */
export function useLoreSmartTags(
  entryId: string
): UseQueryResult<SmartTagsResponse, Error> {
  return useQuery({
    queryKey: smartTagsQueryKeys.lore(entryId),
    queryFn: () => smartTagsApi.getLoreSmartTags(entryId),
    enabled: !!entryId,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

/**
 * Fetch smart tags for a scene
 */
export function useSceneSmartTags(
  storyId: string,
  chapterId: string,
  sceneId: string
): UseQueryResult<SmartTagsResponse, Error> {
  return useQuery({
    queryKey: smartTagsQueryKeys.scene(storyId, chapterId, sceneId),
    queryFn: () => smartTagsApi.getSceneSmartTags(storyId, chapterId, sceneId),
    enabled: !!(storyId && chapterId && sceneId),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

// === Mutation Hooks ===

interface UpdateSmartTagsVariables {
  category: string;
  tags: string[];
  replace?: boolean;
}

/**
 * Update manual smart tags for a lore entry with optimistic updates
 */
export function useUpdateLoreSmartTags(entryId: string) {
  const queryClient = useQueryClient();
  const queryKey = smartTagsQueryKeys.lore(entryId);

  return useMutation({
    mutationFn: (variables: UpdateSmartTagsVariables) =>
      smartTagsApi.updateLoreManualSmartTags(entryId, variables),

    onMutate: async (variables) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey });

      // Snapshot previous value
      const previousData = queryClient.getQueryData<SmartTagsResponse>(queryKey);

      // Optimistically update
      queryClient.setQueryData<SmartTagsResponse>(queryKey, (old) => {
        if (!old) return old;

        const newManualTags = variables.replace
          ? variables.tags
          : [...(old.manual_smart_tags[variables.category] || []), ...variables.tags];

        return {
          ...old,
          manual_smart_tags: {
            ...old.manual_smart_tags,
            [variables.category]: newManualTags,
          },
          effective_tags: {
            ...old.effective_tags,
            [variables.category]: [
              ...newManualTags,
              ...(old.smart_tags[variables.category] || []).filter(
                (tag) => !newManualTags.includes(tag)
              ),
            ],
          },
        };
      });

      // Return context with previous value for rollback
      return { previousData };
    },

    onError: (error, variables, context) => {
      // Rollback to previous value
      if (context?.previousData) {
        queryClient.setQueryData(queryKey, context.previousData);
      }
      toast.error(error instanceof Error ? error.message : 'Failed to update tags');
    },

    onSuccess: (data, variables) => {
      // Server response is authoritative, update with actual data
      queryClient.setQueryData(queryKey, data);

      const action = variables.tags.length === 0 ? 'Cleared' : 'Updated';
      toast.success(`${action} tags for ${variables.category}`);
    },
  });
}

/**
 * Update manual smart tags for a scene with optimistic updates
 */
export function useUpdateSceneSmartTags(
  storyId: string,
  chapterId: string,
  sceneId: string
) {
  const queryClient = useQueryClient();
  const queryKey = smartTagsQueryKeys.scene(storyId, chapterId, sceneId);

  return useMutation({
    mutationFn: (variables: UpdateSmartTagsVariables) =>
      smartTagsApi.updateSceneManualSmartTags(storyId, chapterId, sceneId, variables),

    onMutate: async (variables) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey });

      // Snapshot previous value
      const previousData = queryClient.getQueryData<SmartTagsResponse>(queryKey);

      // Optimistically update
      queryClient.setQueryData<SmartTagsResponse>(queryKey, (old) => {
        if (!old) return old;

        const newManualTags = variables.replace
          ? variables.tags
          : [...(old.manual_smart_tags[variables.category] || []), ...variables.tags];

        return {
          ...old,
          manual_smart_tags: {
            ...old.manual_smart_tags,
            [variables.category]: newManualTags,
          },
          effective_tags: {
            ...old.effective_tags,
            [variables.category]: [
              ...newManualTags,
              ...(old.smart_tags[variables.category] || []).filter(
                (tag) => !newManualTags.includes(tag)
              ),
            ],
          },
        };
      });

      // Return context with previous value for rollback
      return { previousData };
    },

    onError: (error, variables, context) => {
      // Rollback to previous value
      if (context?.previousData) {
        queryClient.setQueryData(queryKey, context.previousData);
      }
      toast.error(error instanceof Error ? error.message : 'Failed to update tags');
    },

    onSuccess: (data, variables) => {
      // Server response is authoritative, update with actual data
      queryClient.setQueryData(queryKey, data);

      const action = variables.tags.length === 0 ? 'Cleared' : 'Updated';
      toast.success(`${action} tags for ${variables.category}`);
    },
  });
}

/**
 * Add a single tag to a lore entry category with optimistic update
 */
export function useAddLoreTag(entryId: string) {
  const queryClient = useQueryClient();
  const queryKey = smartTagsQueryKeys.lore(entryId);

  return useMutation({
    mutationFn: (variables: { category: string; tag: string }) => {
      // Get current data to build the update
      const current = queryClient.getQueryData<SmartTagsResponse>(queryKey);
      const existingManual = current?.manual_smart_tags[variables.category] || [];
      const updatedTags = [...existingManual, variables.tag.trim().toLowerCase()];

      return smartTagsApi.updateLoreManualSmartTags(entryId, {
        category: variables.category,
        tags: updatedTags,
        replace: true,
      });
    },

    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey });

      const previousData = queryClient.getQueryData<SmartTagsResponse>(queryKey);
      const normalizedTag = variables.tag.trim().toLowerCase();

      queryClient.setQueryData<SmartTagsResponse>(queryKey, (old) => {
        if (!old) return old;

        const existingManual = old.manual_smart_tags[variables.category] || [];
        if (existingManual.includes(normalizedTag)) return old;

        const newManualTags = [...existingManual, normalizedTag];

        return {
          ...old,
          manual_smart_tags: {
            ...old.manual_smart_tags,
            [variables.category]: newManualTags,
          },
          effective_tags: {
            ...old.effective_tags,
            [variables.category]: [
              ...newManualTags,
              ...(old.smart_tags[variables.category] || []).filter(
                (tag) => !newManualTags.includes(tag)
              ),
            ],
          },
        };
      });

      return { previousData, tag: normalizedTag };
    },

    onError: (error, variables, context) => {
      if (context?.previousData) {
        queryClient.setQueryData(queryKey, context.previousData);
      }
      toast.error(error instanceof Error ? error.message : 'Failed to add tag');
    },

    onSuccess: (data, variables, context) => {
      queryClient.setQueryData(queryKey, data);
      const tag = context?.tag ?? variables.tag;
      toast.success(`Tag "${tag}" added to ${variables.category}`);
    },
  });
}

/**
 * Add a single tag to a scene category with optimistic update
 */
export function useAddSceneTag(storyId: string, chapterId: string, sceneId: string) {
  const queryClient = useQueryClient();
  const queryKey = smartTagsQueryKeys.scene(storyId, chapterId, sceneId);

  return useMutation({
    mutationFn: (variables: { category: string; tag: string }) => {
      const current = queryClient.getQueryData<SmartTagsResponse>(queryKey);
      const existingManual = current?.manual_smart_tags[variables.category] || [];
      const updatedTags = [...existingManual, variables.tag.trim().toLowerCase()];

      return smartTagsApi.updateSceneManualSmartTags(storyId, chapterId, sceneId, {
        category: variables.category,
        tags: updatedTags,
        replace: true,
      });
    },

    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey });

      const previousData = queryClient.getQueryData<SmartTagsResponse>(queryKey);
      const normalizedTag = variables.tag.trim().toLowerCase();

      queryClient.setQueryData<SmartTagsResponse>(queryKey, (old) => {
        if (!old) return old;

        const existingManual = old.manual_smart_tags[variables.category] || [];
        if (existingManual.includes(normalizedTag)) return old;

        const newManualTags = [...existingManual, normalizedTag];

        return {
          ...old,
          manual_smart_tags: {
            ...old.manual_smart_tags,
            [variables.category]: newManualTags,
          },
          effective_tags: {
            ...old.effective_tags,
            [variables.category]: [
              ...newManualTags,
              ...(old.smart_tags[variables.category] || []).filter(
                (tag) => !newManualTags.includes(tag)
              ),
            ],
          },
        };
      });

      return { previousData, tag: normalizedTag };
    },

    onError: (error, variables, context) => {
      if (context?.previousData) {
        queryClient.setQueryData(queryKey, context.previousData);
      }
      toast.error(error instanceof Error ? error.message : 'Failed to add tag');
    },

    onSuccess: (data, variables, context) => {
      queryClient.setQueryData(queryKey, data);
      const tag = context?.tag ?? variables.tag;
      toast.success(`Tag "${tag}" added to ${variables.category}`);
    },
  });
}

/**
 * Remove a single tag from a lore entry category with optimistic update
 */
export function useRemoveLoreTag(entryId: string) {
  const queryClient = useQueryClient();
  const queryKey = smartTagsQueryKeys.lore(entryId);

  return useMutation({
    mutationFn: (variables: { category: string; tag: string }) => {
      const current = queryClient.getQueryData<SmartTagsResponse>(queryKey);
      const existingManual = current?.manual_smart_tags[variables.category] || [];
      const updatedTags = existingManual.filter((t) => t !== variables.tag);

      return smartTagsApi.updateLoreManualSmartTags(entryId, {
        category: variables.category,
        tags: updatedTags,
        replace: true,
      });
    },

    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey });

      const previousData = queryClient.getQueryData<SmartTagsResponse>(queryKey);

      queryClient.setQueryData<SmartTagsResponse>(queryKey, (old) => {
        if (!old) return old;

        const existingManual = old.manual_smart_tags[variables.category] || [];
        const newManualTags = existingManual.filter((t) => t !== variables.tag);

        return {
          ...old,
          manual_smart_tags: {
            ...old.manual_smart_tags,
            [variables.category]: newManualTags,
          },
          effective_tags: {
            ...old.effective_tags,
            [variables.category]: [
              ...newManualTags,
              ...(old.smart_tags[variables.category] || []).filter(
                (tag) => !newManualTags.includes(tag)
              ),
            ],
          },
        };
      });

      return { previousData };
    },

    onError: (error, variables, context) => {
      if (context?.previousData) {
        queryClient.setQueryData(queryKey, context.previousData);
      }
      toast.error(error instanceof Error ? error.message : 'Failed to remove tag');
    },

    onSuccess: (data, variables) => {
      queryClient.setQueryData(queryKey, data);
      toast.success(`Tag "${variables.tag}" removed from ${variables.category}`);
    },
  });
}

/**
 * Remove a single tag from a scene category with optimistic update
 */
export function useRemoveSceneTag(storyId: string, chapterId: string, sceneId: string) {
  const queryClient = useQueryClient();
  const queryKey = smartTagsQueryKeys.scene(storyId, chapterId, sceneId);

  return useMutation({
    mutationFn: (variables: { category: string; tag: string }) => {
      const current = queryClient.getQueryData<SmartTagsResponse>(queryKey);
      const existingManual = current?.manual_smart_tags[variables.category] || [];
      const updatedTags = existingManual.filter((t) => t !== variables.tag);

      return smartTagsApi.updateSceneManualSmartTags(storyId, chapterId, sceneId, {
        category: variables.category,
        tags: updatedTags,
        replace: true,
      });
    },

    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey });

      const previousData = queryClient.getQueryData<SmartTagsResponse>(queryKey);

      queryClient.setQueryData<SmartTagsResponse>(queryKey, (old) => {
        if (!old) return old;

        const existingManual = old.manual_smart_tags[variables.category] || [];
        const newManualTags = existingManual.filter((t) => t !== variables.tag);

        return {
          ...old,
          manual_smart_tags: {
            ...old.manual_smart_tags,
            [variables.category]: newManualTags,
          },
          effective_tags: {
            ...old.effective_tags,
            [variables.category]: [
              ...newManualTags,
              ...(old.smart_tags[variables.category] || []).filter(
                (tag) => !newManualTags.includes(tag)
              ),
            ],
          },
        };
      });

      return { previousData };
    },

    onError: (error, variables, context) => {
      if (context?.previousData) {
        queryClient.setQueryData(queryKey, context.previousData);
      }
      toast.error(error instanceof Error ? error.message : 'Failed to remove tag');
    },

    onSuccess: (data, variables) => {
      queryClient.setQueryData(queryKey, data);
      toast.success(`Tag "${variables.tag}" removed from ${variables.category}`);
    },
  });
}

/**
 * Clear all tags in a category for a lore entry with optimistic update
 */
export function useClearLoreCategoryTags(entryId: string) {
  const queryClient = useQueryClient();
  const queryKey = smartTagsQueryKeys.lore(entryId);

  return useMutation({
    mutationFn: (category: string) =>
      smartTagsApi.updateLoreManualSmartTags(entryId, {
        category,
        tags: [],
        replace: true,
      }),

    onMutate: async (category) => {
      await queryClient.cancelQueries({ queryKey });

      const previousData = queryClient.getQueryData<SmartTagsResponse>(queryKey);

      queryClient.setQueryData<SmartTagsResponse>(queryKey, (old) => {
        if (!old) return old;

        return {
          ...old,
          manual_smart_tags: {
            ...old.manual_smart_tags,
            [category]: [],
          },
          effective_tags: {
            ...old.effective_tags,
            [category]: old.smart_tags[category] || [],
          },
        };
      });

      return { previousData, category };
    },

    onError: (error, variables, context) => {
      if (context?.previousData) {
        queryClient.setQueryData(queryKey, context.previousData);
      }
      toast.error(error instanceof Error ? error.message : 'Failed to clear tags');
    },

    onSuccess: (_data, _variables, context) => {
      // queryKey is already updated by onSuccess in useUpdateLoreSmartTags pattern
      queryClient.invalidateQueries({ queryKey });
      toast.success(`Cleared all manual tags from ${context?.category}`);
    },
  });
}

/**
 * Clear all tags in a category for a scene with optimistic update
 */
export function useClearSceneCategoryTags(
  storyId: string,
  chapterId: string,
  sceneId: string
) {
  const queryClient = useQueryClient();
  const queryKey = smartTagsQueryKeys.scene(storyId, chapterId, sceneId);

  return useMutation({
    mutationFn: (category: string) =>
      smartTagsApi.updateSceneManualSmartTags(storyId, chapterId, sceneId, {
        category,
        tags: [],
        replace: true,
      }),

    onMutate: async (category) => {
      await queryClient.cancelQueries({ queryKey });

      const previousData = queryClient.getQueryData<SmartTagsResponse>(queryKey);

      queryClient.setQueryData<SmartTagsResponse>(queryKey, (old) => {
        if (!old) return old;

        return {
          ...old,
          manual_smart_tags: {
            ...old.manual_smart_tags,
            [category]: [],
          },
          effective_tags: {
            ...old.effective_tags,
            [category]: old.smart_tags[category] || [],
          },
        };
      });

      return { previousData, category };
    },

    onError: (error, variables, context) => {
      if (context?.previousData) {
        queryClient.setQueryData(queryKey, context.previousData);
      }
      toast.error(error instanceof Error ? error.message : 'Failed to clear tags');
    },

    onSuccess: (_data, _variables, context) => {
      queryClient.invalidateQueries({ queryKey });
      toast.success(`Cleared all manual tags from ${context?.category}`);
    },
  });
}
