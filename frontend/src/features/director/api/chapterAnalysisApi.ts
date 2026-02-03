/**
 * Chapter Analysis API Hooks using TanStack Query
 *
 * Why: Provides type-safe access to chapter health analysis endpoints.
 * Used by the ChapterHealth component to display structural analysis,
 * warnings, and recommendations in Director Mode.
 */
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  ChapterHealthReportSchema,
  type ChapterHealthReport,
} from '@/types/schemas';

/**
 * Query key factory for chapter analysis.
 * Why: Centralizes key creation for consistent cache management.
 */
export const chapterAnalysisKeys = {
  all: ['chapter-analysis'] as const,
  health: (storyId: string, chapterId: string) =>
    [...chapterAnalysisKeys.all, 'health', storyId, chapterId] as const,
};

// ============ Raw API Functions ============

/**
 * Get structural health analysis for a chapter.
 *
 * Why: Returns comprehensive chapter-level analysis including phase
 * distribution, word count estimates, tension arc shape, and detected
 * structural issues for visualization in the ChapterHealth component.
 */
async function getChapterHealth(
  storyId: string,
  chapterId: string
): Promise<ChapterHealthReport> {
  const data = await api.get<unknown>(
    `/structure/stories/${storyId}/chapters/${chapterId}/health`
  );
  return ChapterHealthReportSchema.parse(data);
}

// ============ TanStack Query Hooks ============

/**
 * Hook to fetch structural health analysis for a chapter.
 *
 * Usage:
 * ```tsx
 * const { data, isLoading, error } = useChapterHealth(storyId, chapterId);
 * if (data) {
 *   // Render ChapterHealth with data.warnings, data.health_score, etc.
 * }
 * ```
 */
export function useChapterHealth(
  storyId: string | undefined,
  chapterId: string | undefined
) {
  return useQuery({
    queryKey: chapterAnalysisKeys.health(storyId ?? '', chapterId ?? ''),
    queryFn: () => getChapterHealth(storyId!, chapterId!),
    enabled: !!storyId && !!chapterId,
    // Chapter health data changes less frequently, so we can cache it longer
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

// Export raw functions for non-hook usage
export { getChapterHealth };
