/**
 * Social Network Analysis API
 *
 * Fetches social network metrics for character relationships.
 * Used by the SocialStatsWidget to display key characters.
 */
import { api } from './client';
import {
  SocialAnalysisResponseSchema,
  CharacterCentralitySchema,
  type SocialAnalysisResponse,
  type CharacterCentrality,
} from '@/types/schemas';

/**
 * Fetch complete social network analysis.
 *
 * Returns centrality metrics for all characters, identifies key characters
 * (most connected, most hated, most loved), and provides network properties.
 */
export async function getSocialAnalysis(): Promise<SocialAnalysisResponse> {
  const data = await api.get<SocialAnalysisResponse>('/social/analysis');
  return SocialAnalysisResponseSchema.parse(data);
}

/**
 * Fetch centrality metrics for a specific character.
 *
 * Returns null if the character has no relationships in the network.
 */
export async function getCharacterCentrality(
  characterId: string
): Promise<CharacterCentrality | null> {
  try {
    const data = await api.get<CharacterCentrality>(`/social/analysis/${characterId}`);
    return CharacterCentralitySchema.parse(data);
  } catch (error) {
    // 404 means character has no relationships
    if (
      error &&
      typeof error === 'object' &&
      'status' in error &&
      error.status === 404
    ) {
      return null;
    }
    throw error;
  }
}
