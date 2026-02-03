/**
 * Dialogue generation API
 *
 * Provides API functions for generating character dialogue using AI-powered
 * voice synthesis based on character psychology, traits, and speaking style.
 */
import { api } from '@/lib/api';
import {
  DialogueGenerationRequestSchema,
  DialogueGenerationResponseSchema,
  type DialogueGenerationRequest,
  type DialogueGenerationResponse,
} from '@/types/schemas';

/**
 * Generate dialogue in character voice.
 *
 * Uses the character's psychology (Big Five traits), character traits,
 * and speaking style to produce authentic dialogue that sounds like
 * the character would naturally speak.
 *
 * @param input - The dialogue generation request containing character_id, context, and optional mood
 * @returns Generated dialogue with tone, internal thoughts, and body language
 *
 * @example
 * ```typescript
 * const response = await generateDialogue({
 *   character_id: 'char-123',
 *   context: 'A merchant offers a suspiciously good deal',
 *   mood: 'cautious',
 * });
 * console.log(response.dialogue); // "I've seen deals like this before. What's the catch?"
 * console.log(response.tone);     // "suspicious"
 * ```
 */
export async function generateDialogue(
  input: DialogueGenerationRequest
): Promise<DialogueGenerationResponse> {
  const payload = DialogueGenerationRequestSchema.parse(input);
  const data = await api.post<unknown>('/dialogue/generate', payload);
  return DialogueGenerationResponseSchema.parse(data);
}
