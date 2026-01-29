/**
 * Scene generation API
 */
import { api } from '@/lib/api';
import {
  SceneGenerationRequestSchema,
  SceneGenerationResponseSchema,
  type SceneGenerationRequest,
  type SceneGenerationResponse,
} from '@/types/schemas';

export async function generateScene(
  input: SceneGenerationRequest
): Promise<SceneGenerationResponse> {
  const payload = SceneGenerationRequestSchema.parse(input);
  const data = await api.post<unknown>('/generation/scene', payload);
  return SceneGenerationResponseSchema.parse(data);
}
