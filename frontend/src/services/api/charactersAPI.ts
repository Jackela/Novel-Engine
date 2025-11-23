import { apiClient, handleAPIResponse, handleAPIError } from './apiClient';
import type { BaseAPIResponse } from './apiClient';
import type { Character, PersonalityTraits, CharacterListResponse } from '../../store/slices/charactersSlice';

// Character API request types based on OpenAPI spec
export interface CreateCharacterRequest {
  name: string;
  background_summary?: string;
  personality_traits?: string;
  skills?: Record<string, number>;
  relationships?: Record<string, number>;
  current_location?: string;
}

export interface UpdateCharacterRequest {
  name?: string;
  personality_traits?: PersonalityTraits;
  background?: string;
  configuration?: Record<string, unknown>;
}

export interface GetCharactersParams {
  page?: number;
  limit?: number;
  type?: Character['type'];
  created_after?: string;
  sort?: 'created_at' | 'updated_at' | 'name';
  order?: 'asc' | 'desc';
}

/**
 * Characters API service
 * Handles character management operations
 */
export class CharactersAPI {
  /**
   * List all characters with optional filtering and sorting
   * GET /characters
   */
  async getCharacters(params?: GetCharactersParams): Promise<BaseAPIResponse<CharacterListResponse>> {
    try {
      const response = await apiClient.get('/api/characters', { params });
      const payload = response.data as { characters: string[] };
      const characterIds = payload.characters || [];

      // Fetch detailed info for each character from /api/characters/{id}
      const detailedCharacters = await Promise.all(
        characterIds.map(async (name) => {
          try {
            const detailResponse = await apiClient.get(`/api/characters/${encodeURIComponent(name)}`);
            const detail = detailResponse.data as Record<string, unknown>;
            return this.transformCharacterDetail(name, detail);
          } catch {
            // If detail fetch fails, return basic character with ID
            return this.createBasicCharacter(name);
          }
        })
      );

      return handleAPIResponse({
        ...response,
        data: {
          characters: detailedCharacters,
          pagination: {
            page: 1,
            limit: detailedCharacters.length,
            total_items: detailedCharacters.length,
            total_pages: 1,
            has_next: false,
            has_previous: false,
          },
        },
      } as unknown as typeof response);
    } catch (error) {
      return handleAPIError(error);
    }
  }

  /**
   * Transform backend character detail response to frontend Character type
   */
  private transformCharacterDetail(characterId: string, detail: Record<string, unknown>): Character {
    const structuredData = detail.structured_data as Record<string, unknown> | undefined;
    const psychProfile = structuredData?.psychological_profile as Record<string, number> | undefined;

    return {
      id: characterId,
      name: (detail.name as string) || characterId,
      type: this.inferCharacterType(detail),
      personality_traits: psychProfile ? {
        openness: psychProfile.openness ?? 0.5,
        conscientiousness: psychProfile.conscientiousness ?? 0.5,
        extraversion: psychProfile.extraversion ?? 0.5,
        agreeableness: psychProfile.agreeableness ?? 0.5,
        neuroticism: psychProfile.neuroticism ?? 0.5,
      } : {
        openness: 0.5,
        conscientiousness: 0.5,
        extraversion: 0.5,
        agreeableness: 0.5,
        neuroticism: 0.5,
      },
      background: (detail.background_summary as string) || (detail.narrative_context as string) || '',
      configuration: {
        ai_model: 'gpt-4',
        response_style: 'formal',
        memory_retention: 'medium',
      },
      status: this.mapStatusFromDetail(detail.current_status as string | undefined),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      created_by: 'self',
    };
  }

  /**
   * Create a basic character when detail fetch fails
   */
  private createBasicCharacter(name: string): Character {
    return {
      id: name,
      name: name.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
      type: 'npc',
      personality_traits: {
        openness: 0.5,
        conscientiousness: 0.5,
        extraversion: 0.5,
        agreeableness: 0.5,
        neuroticism: 0.5,
      },
      background: '',
      configuration: {
        ai_model: 'gpt-4',
        response_style: 'formal',
        memory_retention: 'medium',
      },
      status: 'active',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      created_by: 'self',
    };
  }

  /**
   * Infer character type from backend data
   */
  private inferCharacterType(detail: Record<string, unknown>): Character['type'] {
    const narrativeContext = String(detail.narrative_context || '').toLowerCase();
    const backgroundSummary = String(detail.background_summary || '').toLowerCase();
    const combined = `${narrativeContext} ${backgroundSummary}`;

    if (combined.includes('protagonist') || combined.includes('hero') || combined.includes('main character')) {
      return 'protagonist';
    }
    if (combined.includes('antagonist') || combined.includes('villain') || combined.includes('enemy')) {
      return 'antagonist';
    }
    if (combined.includes('narrator') || combined.includes('chronicler')) {
      return 'narrator';
    }
    return 'npc';
  }

  /**
   * Map backend current_status to frontend status
   */
  private mapStatusFromDetail(currentStatus: string | undefined): Character['status'] {
    if (!currentStatus) return 'active';
    const lower = currentStatus.toLowerCase();
    if (lower.includes('inactive') || lower.includes('dormant')) {
      return 'inactive';
    }
    if (lower.includes('archived')) {
      return 'archived';
    }
    return 'active';
  }

  /**
   * Get character by ID
   * GET /characters/{characterId}
   */
  async getCharacter(characterId: string): Promise<BaseAPIResponse<Character>> {
    try {
      const response = await apiClient.get(`/characters/${characterId}`);
      return handleAPIResponse(response);
    } catch (error) {
      return handleAPIError(error);
    }
  }

  /**
   * Create a new character
   * POST /characters
   */
  async createCharacter(characterData: CreateCharacterRequest): Promise<BaseAPIResponse<Character>> {
    try {
      const response = await apiClient.post('/api/characters', characterData);
      const payload = response.data as Record<string, unknown>;

      // Use the actual response data from the backend
      const mapped: Character = this.transformCharacterDetail(
        (payload.id as string) || (payload.name as string) || characterData.name,
        {
          ...payload,
          name: payload.name || characterData.name,
          background_summary: payload.background_summary || characterData.background_summary,
          personality_traits: payload.personality_traits || characterData.personality_traits,
        }
      );

      return handleAPIResponse({ ...response, data: mapped } as unknown as typeof response);
    } catch (error) {
      return handleAPIError(error);
    }
  }

  /**
   * Update character information
   * PUT /characters/{characterId}
   */
  async updateCharacter(
    characterId: string,
    updates: UpdateCharacterRequest
  ): Promise<BaseAPIResponse<Character>> {
    try {
      const response = await apiClient.put(`/characters/${characterId}`, updates);
      return handleAPIResponse(response);
    } catch (error) {
      return handleAPIError(error);
    }
  }

  /**
   * Delete character permanently
   * DELETE /characters/{characterId}
   */
  async deleteCharacter(characterId: string): Promise<BaseAPIResponse<void>> {
    try {
      const response = await apiClient.delete(`/characters/${characterId}`);
      return handleAPIResponse(response);
    } catch (error) {
      return handleAPIError(error);
    }
  }

  /**
   * Batch operations (future enhancement)
   */
  async batchUpdateCharacters(
    _updates: Array<{ id: string; updates: UpdateCharacterRequest }>
  ): Promise<BaseAPIResponse<Character[]>> {
    try {
      // TODO: Implement batch update endpoint when available
      // const response = await apiClient.patch('/characters/batch', { updates });
      // return handleAPIResponse(response);
      
      throw new Error('Batch update not yet implemented');
    } catch (error) {
      return handleAPIError(error);
    }
  }

  /**
   * Get character relationships (future enhancement)
   */
  async getCharacterRelationships(_characterId: string): Promise<BaseAPIResponse<unknown>> {
    try {
      // TODO: Implement relationships endpoint when available
      // const response = await apiClient.get(`/characters/${characterId}/relationships`);
      // return handleAPIResponse(response);
      
      throw new Error('Character relationships not yet implemented');
    } catch (error) {
      return handleAPIError(error);
    }
  }

  /**
   * Get character interaction history (future enhancement)
   */
  async getCharacterHistory(_characterId: string, _params?: {
    limit?: number;
    since?: string;
  }): Promise<BaseAPIResponse<unknown[]>> {
    try {
      // TODO: Implement history endpoint when available
      // const response = await apiClient.get(`/characters/${characterId}/history`, { params });
      // return handleAPIResponse(response);
      
      throw new Error('Character history not yet implemented');
    } catch (error) {
      return handleAPIError(error);
    }
  }

  /**
   * Export character data (future enhancement)
   */
  async exportCharacter(_characterId: string, _format: 'json' | 'csv' = 'json'): Promise<BaseAPIResponse<unknown>> {
    try {
      // TODO: Implement export endpoint when available
      // const response = await apiClient.get(`/characters/${characterId}/export`, {
      //   params: { format }
      // });
      // return handleAPIResponse(response);
      
      throw new Error('Character export not yet implemented');
    } catch (error) {
      return handleAPIError(error);
    }
  }
}

// Export singleton instance
export const charactersAPI = new CharactersAPI();
