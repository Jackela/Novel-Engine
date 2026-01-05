import { apiClient, handleAPIResponse, handleAPIError } from '@/lib/api/apiClient';
import type { BaseAPIResponse } from '@/lib/api/apiClient';
import type { Character, PersonalityTraits, CharacterListResponse } from '@/store/slices/charactersSlice';

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

// Types for batch update operations
export interface BatchUpdateItem {
  id: string;
  updates: UpdateCharacterRequest;
}

export interface BatchUpdateResult {
  succeeded: Character[];
  failed: Array<{
    id: string;
    error: string;
  }>;
}

// Types for character relationships
export interface CharacterRelationship {
  type: 'ally' | 'enemy' | 'neutral' | 'family' | 'romantic' | 'rival' | 'mentor' | 'student';
  target_id: string;
  target_name: string;
  strength?: number; // 0-1 representing relationship strength
  description?: string;
}

export interface CharacterRelationshipsResponse {
  character_id: string;
  relationships: CharacterRelationship[];
}

// Types for character history
export interface CharacterHistoryEvent {
  timestamp: string;
  event: string;
  details?: Record<string, unknown>;
}

export interface CharacterHistoryResponse {
  character_id: string;
  history: CharacterHistoryEvent[];
}

// Types for character export
export interface CharacterExportData {
  character: Character;
  relationships?: CharacterRelationship[];
  history?: CharacterHistoryEvent[];
  exported_at: string;
  format: 'json' | 'csv';
}

export interface GetCharactersParams {
  page?: number;
  limit?: number;
  type?: Character['type'];
  created_after?: string;
  sort?: 'created_at' | 'updated_at' | 'name';
  order?: 'asc' | 'desc';
}

type CharacterSummary = { id: string; name?: string };

/**
 * Characters API service
 * Handles character management operations
 */
export class CharactersAPI {
    private buildCharacterSummaries(rawPayload: unknown): CharacterSummary[] {
      const payload = rawPayload as { characters?: Array<string | { id?: string; name?: string }> };
      const normalizeCharacterSummary = (
        entry: string | { id?: string; name?: string }
      ): CharacterSummary | null => {
        if (typeof entry === 'string') {
          return { id: entry, name: entry };
        }
        if (entry && typeof entry.id === 'string') {
          if (typeof entry.name === 'string') {
            return { id: entry.id, name: entry.name };
          }
          return { id: entry.id };
        }
        if (entry && typeof entry.name === 'string') {
          return { id: entry.name, name: entry.name };
        }
        return null;
      };

      return (payload.characters ?? [])
        .map(normalizeCharacterSummary)
        .filter((entry): entry is CharacterSummary => entry !== null);
    }

    private async fetchCharacterDetail(name: string): Promise<Character> {
      const detailResponse = await apiClient.get(`/api/characters/${encodeURIComponent(name)}`);
      const detail = detailResponse.data as Record<string, unknown>;
      return this.transformCharacterDetail(name, detail);
    }

    private createSummaryFallback(summary: CharacterSummary, name: string): Character {
      return {
        id: summary.id,
        name: summary.name || name,
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
        relationships: {},
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        created_by: 'self',
      } as Character;
    }

    /**
     * List all characters with optional filtering and sorting
     * GET /api/characters
     */
    async getCharacters(params?: GetCharactersParams): Promise<BaseAPIResponse<CharacterListResponse>> {    
      try {
        const response = await apiClient.get('/api/characters', { params });
        const rawPayload = response.data as unknown;
        if (rawPayload && typeof rawPayload === 'object' && 'success' in rawPayload) {
          return rawPayload as BaseAPIResponse<CharacterListResponse>;
        }

        const summaries = this.buildCharacterSummaries(rawPayload);
        const characterIds = summaries.map((entry) => entry.id);

        const detailedCharacters = await Promise.all(
          characterIds.map(async (name) => {
            try {
              return await this.fetchCharacterDetail(name);
            } catch {
              const summary = summaries.find((entry) => entry.id === name);
              if (summary) {
                return this.createSummaryFallback(summary, name);
              }
              return this.createBasicCharacter(name);
            }
          })
        );

        return {
          success: true,
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
          metadata: {
            timestamp: new Date().toISOString(),
            request_id: response.config.metadata?.correlationId ?? `req_${Date.now()}`,
          },
        };
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
     * GET /api/characters/{characterId}
     */
    async getCharacter(characterId: string): Promise<BaseAPIResponse<Character>> {
      try {
        const response = await apiClient.get(`/api/characters/${characterId}`);
        return handleAPIResponse(response);
      } catch (error) {
        return handleAPIError(error);
      }
    }
  
    /**
     * Create a new character
     * POST /api/characters
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
     * PUT /api/characters/{characterId}
     */
    async updateCharacter(
      characterId: string,
      updates: UpdateCharacterRequest
    ): Promise<BaseAPIResponse<Character>> {
      try {
        const response = await apiClient.put(`/api/characters/${characterId}`, updates);
        return handleAPIResponse(response);
      } catch (error) {
        return handleAPIError(error);
      }
    }
  
    /**
     * Delete character permanently
     * DELETE /api/characters/{characterId}
     */
    async deleteCharacter(characterId: string): Promise<BaseAPIResponse<void>> {
      try {
        const response = await apiClient.delete(`/api/characters/${characterId}`);
        return handleAPIResponse(response);
      } catch (error) {
        return handleAPIError(error);
      }
    }
    /**
   * Batch update multiple characters in parallel
   * Uses Promise.all since batch endpoint doesn't exist yet
   * Handles partial failures gracefully
   */
  async batchUpdateCharacters(
    updates: BatchUpdateItem[]
  ): Promise<BaseAPIResponse<BatchUpdateResult>> {
    try {
      // TODO: When batch endpoint is available, use:
      // const response = await apiClient.patch('/characters/batch', { updates });
      // return handleAPIResponse(response);

      // For now, update characters in parallel using individual endpoints
      const results = await Promise.allSettled(
        updates.map(async ({ id, updates: characterUpdates }) => {
          const response = await this.updateCharacter(id, characterUpdates);
          return { id, character: response.data };
        })
      );

      const succeeded: Character[] = [];
      const failed: Array<{ id: string; error: string }> = [];

      results.forEach((result, index) => {
        const sourceUpdate = updates[index];
        if (!sourceUpdate) {
          return;
        }
        const { id } = sourceUpdate;
        if (result.status === 'fulfilled' && result.value.character) {
          succeeded.push(result.value.character);
        } else {
          const errorMessage = result.status === 'rejected'
            ? (result.reason as Error).message || 'Unknown error'
            : 'Update returned no data';
          failed.push({ id, error: errorMessage });
        }
      });

      return {
        success: failed.length === 0,
        data: { succeeded, failed },
        metadata: {
          timestamp: new Date().toISOString(),
          request_id: `batch_${Date.now()}`,
        },
      };
    } catch (error) {
      return handleAPIError(error);
    }
  }

  /**
   * Get character relationships
   * Attempts to fetch from API endpoint, falls back to deriving from character data
   */
  async getCharacterRelationships(characterId: string): Promise<BaseAPIResponse<CharacterRelationshipsResponse>> {
    try {
      // Try to fetch from dedicated endpoint first
      try {
        const response = await apiClient.get(`/api/characters/${encodeURIComponent(characterId)}/relationships`);
        const data = response.data as CharacterRelationshipsResponse;
        return {
          success: true,
          data,
          metadata: {
            timestamp: new Date().toISOString(),
            request_id: `rel_${Date.now()}`,
          },
        };
      } catch {
        // Endpoint doesn't exist, derive relationships from character data
        const characterResponse = await apiClient.get(`/api/characters/${encodeURIComponent(characterId)}`);
        const characterData = characterResponse.data as Record<string, unknown>;

        const relationships = this.deriveRelationshipsFromCharacter(characterId, characterData);

        return {
          success: true,
          data: {
            character_id: characterId,
            relationships,
          },
          metadata: {
            timestamp: new Date().toISOString(),
            request_id: `rel_derived_${Date.now()}`,
            version: 'derived', // Indicates relationships were derived, not from dedicated endpoint
          },
        };
      }
    } catch (error) {
      return handleAPIError(error);
    }
  }

  /**
   * Derive relationships from character data when dedicated endpoint is unavailable
   */
  private deriveRelationshipsFromCharacter(
    _characterId: string,
    characterData: Record<string, unknown>
  ): CharacterRelationship[] {
    const relationships: CharacterRelationship[] = [];

    // Extract structured_data which may contain relationship info
    const structuredData = characterData.structured_data as Record<string, unknown> | undefined;

    // Process allies field
    const allies = (structuredData?.allies || characterData.allies) as string[] | undefined;
    if (Array.isArray(allies)) {
      allies.forEach((ally) => {
        relationships.push({
          type: 'ally',
          target_id: ally,
          target_name: this.formatNameFromId(ally),
          strength: 0.7,
        });
      });
    }

    // Process enemies field
    const enemies = (structuredData?.enemies || characterData.enemies) as string[] | undefined;
    if (Array.isArray(enemies)) {
      enemies.forEach((enemy) => {
        relationships.push({
          type: 'enemy',
          target_id: enemy,
          target_name: this.formatNameFromId(enemy),
          strength: 0.7,
        });
      });
    }

    // Process generic relationships field (Record<string, number> format)
    const relationshipsRecord = characterData.relationships as Record<string, number> | undefined;
    if (relationshipsRecord && typeof relationshipsRecord === 'object') {
      Object.entries(relationshipsRecord).forEach(([targetId, value]) => {
        // Determine relationship type based on value
        // Positive values = ally, negative = enemy, around 0 = neutral
        let type: CharacterRelationship['type'] = 'neutral';
        if (value > 0.3) type = 'ally';
        else if (value < -0.3) type = 'enemy';

        // Avoid duplicates from allies/enemies arrays
        const existing = relationships.find((r) => r.target_id === targetId);
        if (!existing) {
          relationships.push({
            type,
            target_id: targetId,
            target_name: this.formatNameFromId(targetId),
            strength: Math.abs(value),
          });
        }
      });
    }

    return relationships;
  }

  /**
   * Format a character ID into a readable name
   */
  private formatNameFromId(id: string): string {
    return id
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  /**
   * Get character interaction history
   * Attempts to fetch from API endpoint, returns empty history if endpoint unavailable
   */
  async getCharacterHistory(characterId: string, params?: {
    limit?: number;
    since?: string;
  }): Promise<BaseAPIResponse<CharacterHistoryResponse>> {
    try {
      // Try to fetch from dedicated endpoint first
      try {
        const response = await apiClient.get(
          `/api/characters/${encodeURIComponent(characterId)}/history`,
          { params }
        );
        const data = response.data as CharacterHistoryResponse;
        return {
          success: true,
          data,
          metadata: {
            timestamp: new Date().toISOString(),
            request_id: `hist_${Date.now()}`,
          },
        };
      } catch {
        // TODO: When history endpoint is implemented, remove this fallback
        // Endpoint doesn't exist yet, return empty history
        return {
          success: true,
          data: {
            character_id: characterId,
            history: [],
          },
          metadata: {
            timestamp: new Date().toISOString(),
            request_id: `hist_empty_${Date.now()}`,
            version: 'placeholder', // Indicates history endpoint not yet available
          },
        };
      }
    } catch (error) {
      return handleAPIError(error);
    }
  }

  /**
   * Export character data
   * Fetches full character data and formats for export
   */
  async exportCharacter(characterId: string, format: 'json' | 'csv' = 'json'): Promise<BaseAPIResponse<CharacterExportData>> {
    try {
      // Try to use dedicated export endpoint first
      try {
        const response = await apiClient.get(
          `/api/characters/${encodeURIComponent(characterId)}/export`,
          { params: { format } }
        );
        return {
          success: true,
          data: response.data as CharacterExportData,
          metadata: {
            timestamp: new Date().toISOString(),
            request_id: `export_${Date.now()}`,
          },
        };
      } catch {
        // Export endpoint doesn't exist, build export data manually
        // Fetch character data
        const characterResponse = await apiClient.get(`/api/characters/${encodeURIComponent(characterId)}`);
        const rawCharacter = characterResponse.data as Record<string, unknown>;
        const character = this.transformCharacterDetail(characterId, rawCharacter);

        // Optionally fetch relationships (don't fail if unavailable)
        let relationships: CharacterRelationship[] | undefined;
        try {
          const relResponse = await this.getCharacterRelationships(characterId);
          if (relResponse.success && relResponse.data) {
            relationships = relResponse.data.relationships;
          }
        } catch {
          // Relationships not available, continue without them
        }

        // Optionally fetch history (don't fail if unavailable)
        let history: CharacterHistoryEvent[] | undefined;
        try {
          const histResponse = await this.getCharacterHistory(characterId);
          if (histResponse.success && histResponse.data) {
            history = histResponse.data.history;
          }
        } catch {
          // History not available, continue without it
        }

        const exportData: CharacterExportData = {
          character,
          exported_at: new Date().toISOString(),
          format,
          ...(relationships?.length ? { relationships } : {}),
          ...(history?.length ? { history } : {}),
        };

        return {
          success: true,
          data: exportData,
          metadata: {
            timestamp: new Date().toISOString(),
            request_id: `export_composed_${Date.now()}`,
            version: 'composed', // Indicates export was composed from multiple sources
          },
        };
      }
    } catch (error) {
      return handleAPIError(error);
    }
  }

  /**
   * Convert export data to CSV format string
   * Utility method for CSV exports
   */
  formatExportAsCSV(exportData: CharacterExportData): string {
    const { character, relationships, history } = exportData;
    const lines: string[] = [];

    // Character header and data
    lines.push('# Character');
    lines.push('id,name,type,status,background,created_at,updated_at');
    lines.push([
      character.id,
      `"${character.name}"`,
      character.type,
      character.status,
      `"${character.background.replace(/"/g, '""')}"`,
      character.created_at,
      character.updated_at,
    ].join(','));
    lines.push('');

    // Personality traits
    lines.push('# Personality Traits');
    lines.push('openness,conscientiousness,extraversion,agreeableness,neuroticism');
    lines.push([
      character.personality_traits.openness,
      character.personality_traits.conscientiousness,
      character.personality_traits.extraversion,
      character.personality_traits.agreeableness,
      character.personality_traits.neuroticism,
    ].join(','));
    lines.push('');

    // Relationships
    if (relationships?.length) {
      lines.push('# Relationships');
      lines.push('type,target_id,target_name,strength');
      relationships.forEach((rel) => {
        lines.push([
          rel.type,
          rel.target_id,
          `"${rel.target_name}"`,
          rel.strength ?? '',
        ].join(','));
      });
      lines.push('');
    }

    // History
    if (history?.length) {
      lines.push('# History');
      lines.push('timestamp,event,details');
      history.forEach((evt) => {
        lines.push([
          evt.timestamp,
          `"${evt.event.replace(/"/g, '""')}"`,
          evt.details ? `"${JSON.stringify(evt.details).replace(/"/g, '""')}"` : '',
        ].join(','));
      });
    }

    return lines.join('\n');
  }
}

// Export singleton instance
export const charactersAPI = new CharactersAPI();

