/**
 * World generation API
 */
import { api } from '@/lib/api';
import {
  WorldGenerationRequestSchema,
  WorldGenerationResponseSchema,
  type WorldGenerationRequest,
  type WorldGenerationResponse,
} from '@/types/schemas';

export async function generateWorld(
  input: WorldGenerationRequest
): Promise<WorldGenerationResponse> {
  const payload = WorldGenerationRequestSchema.parse(input);
  const data = await api.post<unknown>('/world/generation', payload);
  return WorldGenerationResponseSchema.parse(data);
}
