import { apiClient, handleAPIResponse, handleAPIError } from './apiClient';
import type { BaseAPIResponse } from './apiClient';
import type { Character, PersonalityTraits, CharacterListResponse } from '../../store/slices/charactersSlice';

// Character API request types based on OpenAPI spec
export interface CreateCharacterRequest {
  name: string;
  type: 'protagonist' | 'antagonist' | 'npc' | 'narrator';
  personality_traits: PersonalityTraits;
  background?: string;
  configuration?: {
    ai_model?: 'gpt-4' | 'gpt-3.5-turbo' | 'claude-3';
    response_style?: 'formal' | 'casual' | 'dramatic' | 'humorous';
    memory_retention?: 'low' | 'medium' | 'high';
  };
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
      const response = await apiClient.get('/characters', { params });
      return handleAPIResponse(response);
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
      const response = await apiClient.post('/characters', characterData);
      return handleAPIResponse(response);
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
