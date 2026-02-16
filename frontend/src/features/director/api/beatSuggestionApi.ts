/**
 * Beat Suggestion API - TanStack Query hooks for AI-powered beat suggestions.
 *
 * Why this module:
 *   Provides type-safe API hooks for generating AI beat suggestions
 *   using TanStack Query for caching and loading states.
 */

import { useMutation, type UseMutationResult } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  BeatSuggestionResponseSchema,
  type BeatSuggestionRequest,
  type BeatSuggestionResponse,
} from '@/types/schemas';

/**
 * Query key factory for beat suggestion queries.
 */
export const beatSuggestionKeys = {
  all: ['director', 'beat-suggestions'] as const,
  suggest: (sceneId: string) =>
    ['director', 'beat-suggestions', 'suggest', sceneId] as const,
};

/**
 * Request interface for beat suggestions.
 */
export interface SuggestBeatsInput {
  sceneId: string;
  currentBeats: Array<{ beat_type: string; content: string; mood_shift?: number }>;
  sceneContext: string;
  moodTarget?: number | undefined;
}

/**
 * Suggest beats mutation hook.
 *
 * Generates 3 AI-suggested beats that could follow the current
 * beat sequence based on scene context and mood trajectory.
 *
 * @returns TanStack Query mutation for beat suggestions.
 */
export function useSuggestBeats(): UseMutationResult<
  BeatSuggestionResponse,
  Error,
  SuggestBeatsInput
> {
  return useMutation({
    mutationKey: beatSuggestionKeys.all,
    mutationFn: async (input: SuggestBeatsInput): Promise<BeatSuggestionResponse> => {
      const requestData: BeatSuggestionRequest = {
        scene_id: input.sceneId,
        current_beats: input.currentBeats,
        scene_context: input.sceneContext,
        mood_target: input.moodTarget,
      };
      const data = await api.post<unknown>(
        `/structure/scenes/${input.sceneId}/suggest-beats`,
        requestData
      );
      return BeatSuggestionResponseSchema.parse(data);
    },
  });
}
