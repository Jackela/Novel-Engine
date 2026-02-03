/**
 * Scene Critique API - TanStack Query hooks for AI-powered scene critique.
 *
 * Why this module:
 *   Provides type-safe API hooks for generating AI scene critiques
 *   using TanStack Query for caching and loading states.
 */

import { useMutation, type UseMutationResult } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  CritiqueSceneResponseSchema,
  type CritiqueSceneRequest,
  type CritiqueSceneResponse,
} from '@/types/schemas';

/**
 * Query key factory for scene critique queries.
 */
export const critiqueKeys = {
  all: ['director', 'critique'] as const,
  critique: (sceneId: string) =>
    ['director', 'critique', sceneId] as const,
};

/**
 * Request interface for scene critique.
 */
export interface CritiqueSceneInput {
  sceneId: string;
  sceneText: string;
  sceneGoals?: string[] | undefined;
}

/**
 * Critique scene mutation hook.
 *
 * Generates AI-powered feedback on scene writing quality
 * across multiple craft dimensions (pacing, voice, showing, dialogue).
 *
 * @returns TanStack Query mutation for scene critique.
 */
export function useCritiqueScene(): UseMutationResult<
  CritiqueSceneResponse,
  Error,
  CritiqueSceneInput
> {
  return useMutation({
    mutationKey: critiqueKeys.all,
    mutationFn: async (input: CritiqueSceneInput): Promise<CritiqueSceneResponse> => {
      const requestData: CritiqueSceneRequest = {
        scene_text: input.sceneText,
        scene_goals: input.sceneGoals,
      };
      const data = await api.post<unknown>(
        `/structure/scenes/${input.sceneId}/critique`,
        requestData
      );

      const parsed = CritiqueSceneResponseSchema.safeParse(data);
      if (!parsed.success) {
        console.error('Scene critique response validation failed:', parsed.error);
        throw new Error('Invalid scene critique response from server');
      }

      return parsed.data;
    },
  });
}
