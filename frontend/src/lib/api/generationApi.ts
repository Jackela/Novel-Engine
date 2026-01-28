/**
 * Character generation API
 */
import { api } from '@/lib/api';
import {
  CharacterGenerationRequestSchema,
  CharacterGenerationResponseSchema,
  type CharacterGenerationRequest,
  type CharacterGenerationResponse,
} from '@/types/schemas';

export async function generateCharacter(
  input: CharacterGenerationRequest
): Promise<CharacterGenerationResponse> {
  const payload = CharacterGenerationRequestSchema.parse(input);
  const data = await api.post<unknown>('/generation/character', payload);
  return CharacterGenerationResponseSchema.parse(data);
}
