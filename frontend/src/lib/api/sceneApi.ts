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
  if (typeof window !== 'undefined') {
    (window as { __lastSceneRequest?: SceneGenerationRequest }).__lastSceneRequest =
      payload;
  }
  const headers: Record<string, string> = {};
  if (typeof window !== 'undefined') {
    const mode = (window as { __e2eSceneMode?: string }).__e2eSceneMode;
    const delay = (window as { __e2eSceneDelayMs?: number }).__e2eSceneDelayMs;
    if (mode) {
      headers['x-e2e-scene-mode'] = String(mode);
    }
    if (typeof delay === 'number') {
      headers['x-e2e-scene-delay'] = String(delay);
    }
  }
  const data = await api.post<unknown>('/generation/scene', payload, {
    headers,
  });
  return SceneGenerationResponseSchema.parse(data);
}
