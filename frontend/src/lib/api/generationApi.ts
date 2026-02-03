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
  if (typeof window !== 'undefined') {
    (
      window as { __lastGenerationRequest?: CharacterGenerationRequest }
    ).__lastGenerationRequest = payload;
  }
  const headers: Record<string, string> = {};
  if (typeof window !== 'undefined') {
    const mode = (window as { __e2eGenerationMode?: string }).__e2eGenerationMode;
    const delay = (window as { __e2eGenerationDelayMs?: number })
      .__e2eGenerationDelayMs;
    if (mode) {
      headers['x-e2e-generation-mode'] = String(mode);
    }
    if (typeof delay === 'number') {
      headers['x-e2e-generation-delay'] = String(delay);
    }
  }
  const data = await api.post<unknown>('/generation/character', payload, {
    headers,
  });
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
