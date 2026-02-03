/**
 * Relationship API client functions.
 *
 * Provides functions for interacting with the relationships API endpoints,
 * including relationship history generation.
 */
import { api } from './client';
import {
  RelationshipHistoryGenerationResponseSchema,
  type RelationshipHistoryGenerationResponse,
} from '@/types/schemas';

/**
 * Generate a backstory for a relationship using AI.
 *
 * Creates a compelling narrative explaining how two characters developed
 * their current trust and romance levels.
 *
 * @param relationshipId - The ID of the relationship to generate history for.
 * @returns Generated backstory with first meeting, defining moment, and current status.
 */
export async function generateRelationshipHistory(
  relationshipId: string
): Promise<RelationshipHistoryGenerationResponse> {
  const response = await api.post<unknown>(
    `/relationships/${relationshipId}/generate-history`
  );
  return RelationshipHistoryGenerationResponseSchema.parse(response);
}
