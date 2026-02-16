/**
 * Smart Tags API
 *
 * BRAIN-038-05: Manual Tag Override
 * API client for smart tags management endpoints
 */

export interface SmartTagsResponse {
  smart_tags: Record<string, string[]>;
  manual_smart_tags: Record<string, string[]>;
  effective_tags: Record<string, string[]>;
}

export interface ManualSmartTagsUpdateRequest {
  category: string;
  tags: string[];
  replace?: boolean;
}

const API_BASE = '/api';

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || error.message || 'Request failed');
  }
  return response.json();
}

export const smartTagsApi = {
  /**
   * Get smart tags for a lore entry
   */
  async getLoreSmartTags(entryId: string): Promise<SmartTagsResponse> {
    const response = await fetch(
      `${API_BASE}/lore/${encodeURIComponent(entryId)}/smart-tags`
    );
    return handleResponse<SmartTagsResponse>(response);
  },

  /**
   * Update manual smart tags for a lore entry
   */
  async updateLoreManualSmartTags(
    entryId: string,
    request: ManualSmartTagsUpdateRequest
  ): Promise<SmartTagsResponse> {
    const response = await fetch(
      `${API_BASE}/lore/${encodeURIComponent(entryId)}/smart-tags/manual`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      }
    );
    return handleResponse<SmartTagsResponse>(response);
  },

  /**
   * Delete manual smart tags for a lore entry category
   */
  async deleteLoreManualSmartTags(entryId: string, category: string): Promise<void> {
    const response = await fetch(
      `${API_BASE}/lore/${encodeURIComponent(entryId)}/smart-tags/manual/${encodeURIComponent(category)}`,
      { method: 'DELETE' }
    );
    if (!response.ok && response.status !== 204) {
      const error = await response
        .json()
        .catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || 'Delete failed');
    }
  },

  /**
   * Get smart tags for a scene
   */
  async getSceneSmartTags(
    storyId: string,
    chapterId: string,
    sceneId: string
  ): Promise<SmartTagsResponse> {
    const response = await fetch(
      `${API_BASE}/structure/stories/${encodeURIComponent(storyId)}/chapters/${encodeURIComponent(chapterId)}/scenes/${encodeURIComponent(sceneId)}/smart-tags`
    );
    return handleResponse<SmartTagsResponse>(response);
  },

  /**
   * Update manual smart tags for a scene
   */
  async updateSceneManualSmartTags(
    storyId: string,
    chapterId: string,
    sceneId: string,
    request: ManualSmartTagsUpdateRequest
  ): Promise<SmartTagsResponse> {
    const response = await fetch(
      `${API_BASE}/structure/stories/${encodeURIComponent(storyId)}/chapters/${encodeURIComponent(chapterId)}/scenes/${encodeURIComponent(sceneId)}/smart-tags/manual`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      }
    );
    return handleResponse<SmartTagsResponse>(response);
  },

  /**
   * Delete manual smart tags for a scene category
   */
  async deleteSceneManualSmartTags(
    storyId: string,
    chapterId: string,
    sceneId: string,
    category: string
  ): Promise<void> {
    const response = await fetch(
      `${API_BASE}/structure/stories/${encodeURIComponent(storyId)}/chapters/${encodeURIComponent(chapterId)}/scenes/${encodeURIComponent(sceneId)}/smart-tags/manual/${encodeURIComponent(category)}`,
      { method: 'DELETE' }
    );
    if (!response.ok && response.status !== 204) {
      const error = await response
        .json()
        .catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || 'Delete failed');
    }
  },
};
