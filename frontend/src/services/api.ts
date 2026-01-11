// Novel Engine API Service
// Centralized API communication layer

import type { AxiosInstance } from 'axios';
import apiClient, { handleAPIError } from '@/lib/api/apiClient';
import type {
  Character,
  StoryProject,
  SystemStatus,
  ApiResponse,
  CharacterFormData,
  StoryFormData,
  ExportOptions
} from '@/types';
import type {
  CharacterSummary,
  CharactersListResponse,
  CharacterDetailResponse,
  EnhancedCharacterResponse,
} from '@/types/dto';
import { logger } from './logging/LoggerFactory';
import {
  transformCharacterResponse,
  transformEnhancedCharacterResponse,
  transformCharacterCreationResponse,
  transformSimulationResponse
} from './dtoTransforms';


// Note: Custom in-memory cache removed; server-state caching handled by consumers (e.g., React Query).

/**
 * Generate agent_id from character name
 * Matches backend logic in persona_core.py:230-243
 */
const generateAgentId = (name: string): string => {
  // Convert to lowercase and replace spaces/hyphens with underscores
  let agentId = name.toLowerCase()
    .replace(/\s+/g, '_')
    .replace(/-/g, '_')
    .replace(/[^a-z0-9_]/g, '');

  // Ensure doesn't start with a number
  if (agentId && /^\d/.test(agentId)) {
    agentId = `agent_${agentId}`;
  }

  // Fallback for empty string
  if (!agentId) {
    agentId = `agent_${Date.now() % 10000}`;
  }

  // Ensure minimum length of 3 characters
  if (agentId.length < 3) {
    agentId = `agent_${agentId}`;
  }

  // Ensure maximum length of 50 characters
  if (agentId.length > 50) {
    agentId = agentId.substring(0, 50);
  }

  return agentId;
};

/**
 * Normalize skill value from 1-10 range to 0.0-1.0 range
 * Backend expects skills in 0.0-1.0 range
 */
const normalizeSkillValue = (value: number): number => {
  // Transform from 1-10 to 0.0-1.0
  // Using (value - 1) / 9 to map: 1→0.0, 5→0.444, 10→1.0
  return Math.max(0.0, Math.min(1.0, (value - 1) / 9));
};

class NovelEngineAPI {
  private readonly client: AxiosInstance;

  constructor(client: AxiosInstance = apiClient) {
    this.client = client;
  }

  private fail(error: unknown): never {
    return handleAPIError(error);
  }

  // System and Health APIs
  async getHealth(): Promise<SystemStatus> {
    try {
      const response = await this.client.get<SystemStatus>('/health');
      return response.data;
    } catch (error) {
      return this.fail(error);
    }
  }

  async getSystemStatus(): Promise<SystemStatus> {
    try {
      const response = await this.client.get<SystemStatus>('/meta/system-status');
      return response.data;
    } catch (error) {
      return this.fail(error);
    }
  }

  // Enhanced Character APIs with caching
  async getCharacters(): Promise<CharacterSummary[]> {
    try {
      const response = await this.client.get<CharactersListResponse>('/api/characters');
      return response.data.characters;
    } catch (error) {
      return this.fail(error);
    }
  }

  async getCharacterDetails(name: string): Promise<Character> {
    try {
      const response = await this.client.get<CharacterDetailResponse>(`/api/characters/${encodeURIComponent(name)}`);
      return transformCharacterResponse(response.data, name);
    } catch (error) {
      return this.fail(error);
    }
  }

  async getCharacter(name: string): Promise<Character> {
    return this.getCharacterDetails(name);
  }

  async getEnhancedCharacterData(name: string): Promise<Character> {
    try {
      const response = await this.client.get<EnhancedCharacterResponse>(`/api/characters/${encodeURIComponent(name)}/enhanced`);
      return transformEnhancedCharacterResponse(response.data);
    } catch (error) {
      logger.warn(`Enhanced character data failed for ${name}, falling back: ${(error as Error).message}`);
      return this.getCharacterDetails(name);
    }
  }

  async createCharacter(characterData: CharacterFormData, files?: File[]): Promise<ApiResponse<Character>> {
    void files;

    // Generate agent_id from character name
    const agentId = generateAgentId(characterData.name);

    // Normalize skills from 1-10 range to 0.0-1.0 range
    const normalizedSkills = Object.entries(characterData.stats).reduce(
      (acc, [key, value]) => ({
        ...acc,
        [key]: normalizeSkillValue(value),
      }),
      {} as Record<string, number>
    );

    const request = {
      agent_id: agentId,
      name: characterData.name,
      background_summary: characterData.description,
      personality_traits: characterData.role,
      skills: normalizedSkills,
      inventory: characterData.equipment.map((item) => item.name),
      metadata: {
        faction: characterData.faction,
        role: characterData.role,
      },
      structured_data: {
        faction: characterData.faction,
        role: characterData.role,
        stats: characterData.stats,
        equipment: characterData.equipment,
        relationships: characterData.relationships,
      },
    };

    try {
      const response = await this.client.post<Record<string, unknown>>('/api/characters', request);
      const character = transformCharacterCreationResponse(response.data, characterData);
      return {
        success: true,
        data: character,
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      return this.fail(error);
    }
  }

  async updateCharacter(characterId: string, characterData: CharacterFormData, files?: File[]): Promise<ApiResponse<Character>> {
    void files;

    // Generate agent_id from character name (for consistency)
    const agentId = generateAgentId(characterData.name);

    // Normalize skills from 1-10 range to 0.0-1.0 range
    const normalizedSkills = Object.entries(characterData.stats).reduce(
      (acc, [key, value]) => ({
        ...acc,
        [key]: normalizeSkillValue(value),
      }),
      {} as Record<string, number>
    );

    const request = {
      agent_id: agentId,
      name: characterData.name,
      background_summary: characterData.description,
      personality_traits: characterData.role,
      skills: normalizedSkills,
      inventory: characterData.equipment.map((item) => item.name),
      metadata: {
        faction: characterData.faction,
        role: characterData.role,
      },
      structured_data: {
        faction: characterData.faction,
        role: characterData.role,
        stats: characterData.stats,
        equipment: characterData.equipment,
        relationships: characterData.relationships,
      },
    };

    try {
      const response = await this.client.put<CharacterDetailResponse>(
        `/api/characters/${encodeURIComponent(characterId)}`,
        request
      );

      return {
        success: true,
        data: transformCharacterResponse(response.data, characterId),
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      return this.fail(error);
    }
  }

  async deleteCharacter(characterId: string): Promise<ApiResponse<void>> {
    try {
      await this.client.delete(`/api/characters/${encodeURIComponent(characterId)}`);
      return { success: true, timestamp: new Date().toISOString() };
    } catch (error) {
      return this.fail(error);
    }
  }

  // Story and Simulation APIs
  async runSimulation(storyData: StoryFormData): Promise<ApiResponse<StoryProject> & { generation_id?: string }> {
    try {
      const orchestrationRequest = {
        character_names: storyData.characters,
        total_turns: storyData.settings.turns || 3,
        start_turn: 1
      };

      // Call the orchestration start endpoint
      type OrchestrationStartResponse = {
        success: boolean;
        data: Record<string, unknown>;
      };
      const response = await this.client.post<OrchestrationStartResponse>(
        '/api/orchestration/start',
        orchestrationRequest
      );

      const storyProject = transformSimulationResponse(response.data.data, storyData);

      return {
        success: response.data.success,
        generation_id: 'orchestration_active', // Singleton state, so ID is static/irrelevant
        data: storyProject,
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      return this.fail(error);
    }
  }

  async getGenerationStatus(generationId: string): Promise<{ generation_id: string; status: string; progress: number; stage: string; estimated_time_remaining: number; }> {
    try {
      const response = await this.client.get<{ generation_id: string; status: string; progress: number; stage: string; estimated_time_remaining: number; }>(`/api/stories/status/${generationId}`);
      return response.data;
    } catch (error) {
      return this.fail(error);
    }
  }

  // Campaign APIs
  async getCampaigns(): Promise<string[]> {
    try {
      const response = await this.client.get<{ campaigns: string[] }>('/campaigns');
      return response.data.campaigns;
    } catch (error) {
      return this.fail(error);
    }
  }

  async createCampaign(name: string, description?: string): Promise<ApiResponse<{ id: string; name: string; description: string }>> {
    try {
      const response = await this.client.post<{ id: string; name: string; description: string }>('/campaigns', {
        campaign_name: name,
        description: description || '',
      });

      return {
        success: true,
        data: response.data,
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      return this.fail(error);
    }
  }

  // Cache management methods removed (use consumer-level caching)
  // Utility methods
  async testConnection(): Promise<boolean> {
    try {
      await this.getHealth();
      return true;
    } catch (error) {
      logger.error('Connection test failed:', error as Error);
      return false;
    }
  }

  getBaseURL(): string {
    return this.client.defaults.baseURL || '';
  }

  // Connection quality monitoring
  async testConnectionQuality(): Promise<{
    connected: boolean;
    latency: number;
    timestamp: number;
  }> {
    const start = performance.now();
    try {
      await this.getHealth();
      const latency = performance.now() - start;
      return {
        connected: true,
        latency,
        timestamp: Date.now(),
      };
    } catch (_error) {
      void _error;
      return {
        connected: false,
        latency: -1,
        timestamp: Date.now(),
      };
    }
  }

  // Export functionality (to be implemented)
  async exportStory(_projectId: string, _options: ExportOptions): Promise<Blob> {
    // This would integrate with a future export endpoint
    throw new Error('Export functionality not yet implemented');
  }
}

export const api = new NovelEngineAPI();
export default api;
