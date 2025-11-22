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
      const mapped: Character[] = (payload.characters || []).map((name, idx) => ({
        id: name,
        name,
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
      }));
      return handleAPIResponse({
        ...response,
        data: {
          characters: mapped,
          pagination: {
            page: 1,
            limit: mapped.length,
            total_items: mapped.length,
            total_pages: 1,
            has_next: false,
            has_previous: false,
          },
        },
      } as any);
    } catch (error) {
      return handleAPIError(error);
    }
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
      const payload = response.data as any;
      const mapped: Character = {
        id: payload.id || payload.name,
        name: payload.name,
        type: 'npc',
        personality_traits: {
          openness: 0.5,
          conscientiousness: 0.5,
          extraversion: 0.5,
          agreeableness: 0.5,
          neuroticism: 0.5,
        },
        background: payload.background_summary || '',
        configuration: {
          ai_model: 'gpt-4',
          response_style: 'formal',
          memory_retention: 'medium',
        },
        status: 'active',
        created_at: payload.created_at || new Date().toISOString(),
        updated_at: payload.updated_at || new Date().toISOString(),
        created_by: payload.user_id || 'self',
      };
      return handleAPIResponse({ ...response, data: mapped } as any);
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
