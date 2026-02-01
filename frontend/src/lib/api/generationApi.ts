/**
 * Character generation API
 */
import { api } from '@/lib/api';
import {
  CharacterGenerationRequestSchema,
  CharacterGenerationResponseSchema,
  CharacterProfileGenerationRequestSchema,
  CharacterProfileGenerationResponseSchema,
  type CharacterGenerationRequest,
  type CharacterGenerationResponse,
  type CharacterProfileGenerationRequest,
  type CharacterProfileGenerationResponse,
} from '@/types/schemas';

export async function generateCharacter(
  input: CharacterGenerationRequest
): Promise<CharacterGenerationResponse> {
  const payload = CharacterGenerationRequestSchema.parse(input);
  const data = await api.post<unknown>('/generation/character', payload);
  return CharacterGenerationResponseSchema.parse(data);
}

/**
 * Generate a detailed character profile using LLM or mock generator.
 *
 * This API generates a complete character profile including aliases, traits,
 * appearance, backstory, motivations, and quirks based on the provided
 * name, archetype, and optional context.
 */
export async function generateCharacterProfile(
  input: CharacterProfileGenerationRequest
): Promise<CharacterProfileGenerationResponse> {
  const payload = CharacterProfileGenerationRequestSchema.parse(input);
  const data = await api.post<unknown>('/generation/character-profile', payload);
  return CharacterProfileGenerationResponseSchema.parse(data);
}
