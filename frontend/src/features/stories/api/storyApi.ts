/**
 * Story API hooks using TanStack Query
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import type { Story, GenerateStoryInput, StoryGenerationProgress } from '@/shared/types/story';

const STORIES_KEY = ['stories'];

// Fetch stories for a campaign
export function useStories(campaignId?: string) {
  return useQuery({
    queryKey: [...STORIES_KEY, { campaignId }],
    queryFn: () => api.get<Story[]>('/stories', { params: { campaignId } }),
    enabled: !!campaignId,
  });
}

// Fetch all stories
export function useAllStories() {
  return useQuery({
    queryKey: STORIES_KEY,
    queryFn: () => api.get<Story[]>('/stories'),
  });
}

// Fetch single story
export function useStory(id: string) {
  return useQuery({
    queryKey: [...STORIES_KEY, id],
    queryFn: () => api.get<Story>(`/stories/${id}`),
    enabled: !!id,
  });
}

// Generate new story
export function useGenerateStory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: GenerateStoryInput) =>
      api.post<StoryGenerationProgress>('/stories/generate', input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: STORIES_KEY });
    },
  });
}

// Delete story
export function useDeleteStory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.delete(`/stories/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: STORIES_KEY });
    },
  });
}

// Export story
export function useExportStory() {
  return useMutation({
    mutationFn: ({ id, format }: { id: string; format: 'markdown' | 'pdf' | 'json' }) =>
      api.get<Blob>(`/stories/${id}/export`, {
        params: { format },
        headers: { Accept: format === 'pdf' ? 'application/pdf' : 'application/octet-stream' },
      }),
  });
}
