/**
 * Narrative Structure API
 *
 * Why: Provides type-safe access to the Story/Chapter/Scene CRUD endpoints,
 * enabling the Outliner UI to manage narrative structure through the backend.
 */
import { api } from '@/lib/api';
import {
  StoryResponseSchema,
  StoryListResponseSchema,
  ChapterResponseSchema,
  ChapterListResponseSchema,
  SceneResponseSchema,
  SceneListResponseSchema,
  StoryCreateRequestSchema,
  ChapterCreateRequestSchema,
  SceneCreateRequestSchema,
  type StoryResponse,
  type StoryListResponse,
  type ChapterResponse,
  type ChapterListResponse,
  type SceneResponse,
  type SceneListResponse,
  type StoryCreateRequest,
  type ChapterCreateRequest,
  type SceneCreateRequest,
} from '@/types/schemas';

// ============ Story Operations ============

/**
 * List all stories.
 *
 * Why: Provides the initial data load for story selection UI.
 */
export async function listStories(): Promise<StoryListResponse> {
  const data = await api.get<unknown>('/structure/stories');
  return StoryListResponseSchema.parse(data);
}

/**
 * Get a single story by ID.
 */
export async function getStory(storyId: string): Promise<StoryResponse> {
  const data = await api.get<unknown>(`/structure/stories/${storyId}`);
  return StoryResponseSchema.parse(data);
}

/**
 * Create a new story.
 */
export async function createStory(input: StoryCreateRequest): Promise<StoryResponse> {
  const payload = StoryCreateRequestSchema.parse(input);
  const data = await api.post<unknown>('/structure/stories', payload);
  return StoryResponseSchema.parse(data);
}

/**
 * Update a story.
 */
export async function updateStory(
  storyId: string,
  updates: Partial<StoryCreateRequest> & { status?: 'draft' | 'published' }
): Promise<StoryResponse> {
  const data = await api.patch<unknown>(`/structure/stories/${storyId}`, updates);
  return StoryResponseSchema.parse(data);
}

/**
 * Delete a story.
 */
export async function deleteStory(storyId: string): Promise<void> {
  await api.delete<unknown>(`/structure/stories/${storyId}`);
}

// ============ Chapter Operations ============

/**
 * List all chapters in a story.
 *
 * Why: Provides the chapter data for the Outliner sidebar.
 */
export async function listChapters(storyId: string): Promise<ChapterListResponse> {
  const data = await api.get<unknown>(`/structure/stories/${storyId}/chapters`);
  return ChapterListResponseSchema.parse(data);
}

/**
 * Get a single chapter by ID.
 */
export async function getChapter(
  storyId: string,
  chapterId: string
): Promise<ChapterResponse> {
  const data = await api.get<unknown>(
    `/structure/stories/${storyId}/chapters/${chapterId}`
  );
  return ChapterResponseSchema.parse(data);
}

/**
 * Create a new chapter in a story.
 */
export async function createChapter(
  storyId: string,
  input: ChapterCreateRequest
): Promise<ChapterResponse> {
  const payload = ChapterCreateRequestSchema.parse(input);
  const data = await api.post<unknown>(
    `/structure/stories/${storyId}/chapters`,
    payload
  );
  return ChapterResponseSchema.parse(data);
}

/**
 * Update a chapter.
 */
export async function updateChapter(
  storyId: string,
  chapterId: string,
  updates: Partial<ChapterCreateRequest> & { status?: 'draft' | 'published' }
): Promise<ChapterResponse> {
  const data = await api.patch<unknown>(
    `/structure/stories/${storyId}/chapters/${chapterId}`,
    updates
  );
  return ChapterResponseSchema.parse(data);
}

/**
 * Delete a chapter.
 */
export async function deleteChapter(storyId: string, chapterId: string): Promise<void> {
  await api.delete<unknown>(`/structure/stories/${storyId}/chapters/${chapterId}`);
}

/**
 * Move a chapter to a new position.
 */
export async function moveChapter(
  storyId: string,
  chapterId: string,
  newOrderIndex: number
): Promise<ChapterResponse> {
  const data = await api.post<unknown>(
    `/structure/stories/${storyId}/chapters/${chapterId}/move`,
    { new_order_index: newOrderIndex }
  );
  return ChapterResponseSchema.parse(data);
}

// ============ Scene Operations ============

/**
 * List all scenes in a chapter.
 *
 * Why: Provides scene data for the nested tree-view in the Outliner.
 */
export async function listScenes(
  storyId: string,
  chapterId: string
): Promise<SceneListResponse> {
  const data = await api.get<unknown>(
    `/structure/stories/${storyId}/chapters/${chapterId}/scenes`
  );
  return SceneListResponseSchema.parse(data);
}

/**
 * Get a single scene by ID.
 */
export async function getScene(
  storyId: string,
  chapterId: string,
  sceneId: string
): Promise<SceneResponse> {
  const data = await api.get<unknown>(
    `/structure/stories/${storyId}/chapters/${chapterId}/scenes/${sceneId}`
  );
  return SceneResponseSchema.parse(data);
}

/**
 * Create a new scene in a chapter.
 */
export async function createScene(
  storyId: string,
  chapterId: string,
  input: SceneCreateRequest
): Promise<SceneResponse> {
  const payload = SceneCreateRequestSchema.parse(input);
  const data = await api.post<unknown>(
    `/structure/stories/${storyId}/chapters/${chapterId}/scenes`,
    payload
  );
  return SceneResponseSchema.parse(data);
}

/**
 * Update a scene.
 */
export async function updateScene(
  storyId: string,
  chapterId: string,
  sceneId: string,
  updates: Partial<SceneCreateRequest> & {
    status?: 'draft' | 'generating' | 'review' | 'published';
  }
): Promise<SceneResponse> {
  const data = await api.patch<unknown>(
    `/structure/stories/${storyId}/chapters/${chapterId}/scenes/${sceneId}`,
    updates
  );
  return SceneResponseSchema.parse(data);
}

/**
 * Delete a scene.
 */
export async function deleteScene(
  storyId: string,
  chapterId: string,
  sceneId: string
): Promise<void> {
  await api.delete<unknown>(
    `/structure/stories/${storyId}/chapters/${chapterId}/scenes/${sceneId}`
  );
}

/**
 * Move a scene to a new position, optionally to a different chapter.
 */
export async function moveScene(
  storyId: string,
  chapterId: string,
  sceneId: string,
  newOrderIndex: number,
  targetChapterId?: string
): Promise<SceneResponse> {
  const data = await api.post<unknown>(
    `/structure/stories/${storyId}/chapters/${chapterId}/scenes/${sceneId}/move`,
    {
      new_order_index: newOrderIndex,
      ...(targetChapterId ? { target_chapter_id: targetChapterId } : {}),
    }
  );
  return SceneResponseSchema.parse(data);
}
