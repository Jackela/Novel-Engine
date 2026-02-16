/**
 * Pacing API Hooks using TanStack Query
 *
 * Why: Provides type-safe access to chapter pacing analysis endpoints.
 * Used by the PacingGraph component to visualize tension/energy curves
 * and detect pacing issues in Director Mode.
 */
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  ChapterPacingResponseSchema,
  type ChapterPacingResponse,
} from '@/types/schemas';

/**
 * Query key factory for pacing.
 * Why: Centralizes key creation for consistent cache management.
 */
export const pacingKeys = {
  all: ['pacing'] as const,
  chapter: (storyId: string, chapterId: string) =>
    [...pacingKeys.all, 'chapter', storyId, chapterId] as const,
};

// ============ Raw API Functions ============

/**
 * Get pacing analysis for a chapter.
 *
 * Why: Returns scene-by-scene tension/energy metrics and detected issues
 * for visualization in the PacingGraph component.
 */
async function getChapterPacing(
  storyId: string,
  chapterId: string
): Promise<ChapterPacingResponse> {
  const data = await api.get<unknown>(
    `/structure/stories/${storyId}/chapters/${chapterId}/pacing`
  );
  return ChapterPacingResponseSchema.parse(data);
}

// ============ TanStack Query Hooks ============

/**
 * Hook to fetch pacing analysis for a chapter.
 *
 * Usage:
 * ```tsx
 * const { data, isLoading, error } = useChapterPacing(storyId, chapterId);
 * if (data) {
 *   // Render PacingGraph with data.scene_metrics
 * }
 * ```
 */
export function useChapterPacing(
  storyId: string | undefined,
  chapterId: string | undefined
) {
  return useQuery({
    queryKey: pacingKeys.chapter(storyId ?? '', chapterId ?? ''),
    queryFn: () => getChapterPacing(storyId!, chapterId!),
    enabled: !!storyId && !!chapterId,
    // Pacing data doesn't change frequently, so we can cache it longer
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Export raw functions for non-hook usage
export { getChapterPacing };
