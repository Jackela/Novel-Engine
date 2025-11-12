// Novel Engine API Service
// Centralized API communication layer

import axios, { isAxiosError } from 'axios';
import type { AxiosInstance } from 'axios';
import type { 
  Character, 
  StoryProject, 
  SystemStatus,
  ApiResponse,
  CharacterFormData,
  StoryFormData,
  ExportOptions
} from '../types';
import type { 
  CharactersListResponse,
  CharacterDetailResponse,
  EnhancedCharacterResponse,
  GenerateStoryResponse,
  SimulationLegacyResponse,
  CharacterStructuredData,
} from '../types/dto';
import type { CharacterStats, Equipment } from '../types';
import { logger } from './logging/LoggerFactory';

type SimulationData = Partial<SimulationLegacyResponse> & { participants?: string[] };

// Note: Custom in-memory cache removed; server-state caching handled by consumers (e.g., React Query).

class NovelEngineAPI {
  private client: AxiosInstance;
  private baseURL: string;
  // No internal caches; rely on consumer-level caching.

  constructor(baseURL: string = 'http://localhost:8000') {
    this.baseURL = baseURL;
    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });

    // Request interceptor for logging and auth
    this.client.interceptors.request.use(
      (config) => {
        logger.debug(`API Request: ${config.method?.toUpperCase()} ${config.url}`, {
          component: 'NovelEngineAPI',
          action: 'request',
        });
        return config;
      },
      (error) => {
        logger.error('API Request Error', error as Error, {
          component: 'NovelEngineAPI',
          action: 'request',
        });
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => {
        logger.debug(`API Response: ${response.status} ${response.config.url}`, {
          component: 'NovelEngineAPI',
          action: 'response',
        });
        return response;
      },
      (error) => {
        logger.error('API Response Error', error as Error, {
          component: 'NovelEngineAPI',
          action: 'response',
          errorData: error.response?.data || error.message,
        });
        return Promise.reject(this.handleError(error));
      }
    );
  }

  private handleError(error: unknown): Error {
    if (isAxiosError(error)) {
      if (error.response) {
        const data = error.response.data as { detail?: string; message?: string } | undefined;
        const message = data?.detail || data?.message || 'Server error';
        return new Error(`API Error (${error.response.status}): ${message}`);
      }
      if (error.request) {
        return new Error('Network error: Unable to connect to server');
      }
      return new Error(`Request error: ${error.message}`);
    }
    return new Error('Unknown error');
  }

  // System and Health APIs
  async getHealth(): Promise<SystemStatus> {
    const response = await this.client.get<SystemStatus>('/health');
    return response.data;
  }

  async getSystemStatus(): Promise<SystemStatus> {
    const response = await this.client.get<SystemStatus>('/meta/system-status');
    return response.data;
  }

  // Enhanced Character APIs with caching
  async getCharacters(): Promise<string[]> {
    const response = await this.client.get<CharactersListResponse>('/characters');
    return response.data.characters;
  }

  async getCharacterDetails(name: string): Promise<Character> {
    const response = await this.client.get<CharacterDetailResponse>(`/characters/${encodeURIComponent(name)}`);
    return this.transformCharacterResponse(response.data, name);
  }

  async getEnhancedCharacterData(name: string): Promise<Character> {
    try {
      const response = await this.client.get<EnhancedCharacterResponse>(`/characters/${encodeURIComponent(name)}/enhanced`);
      return this.transformEnhancedCharacterResponse(response.data);
    } catch (error) {
      logger.warn(`Enhanced character data failed for ${name}, falling back: ${(error as Error).message}`);
      return this.getCharacterDetails(name);
    }
  }

  async createCharacter(characterData: CharacterFormData, files?: File[]): Promise<ApiResponse<Character>> {
    const formData = new FormData();
    formData.append('name', characterData.name);
    formData.append('description', characterData.description);

    if (files && files.length > 0) {
      files.forEach(file => {
        formData.append('files', file);
      });
    }

    const response = await this.client.post<unknown>('/characters', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    const character = this.transformCharacterCreationResponse(response.data as Record<string, unknown>, characterData);
    
    // Client caches managed by consumers (e.g., React Query). No internal cache.

    return {
      success: true,
      data: character,
      timestamp: new Date().toISOString(),
    };
  }

  // Story and Simulation APIs
  async runSimulation(storyData: StoryFormData): Promise<ApiResponse<StoryProject> & { generation_id?: string }> {
    // First try the new story generation API with real-time progress
    try {
      const generationRequest = {
        characters: storyData.characters,
        title: storyData.title,
      };
      const response = await this.client.post<GenerateStoryResponse>('/api/v1/stories/generate', generationRequest as unknown as Record<string, unknown>);
      
      // Return response with generation_id for WebSocket tracking
      return {
        success: true,
        generation_id: response.data.generation_id,
        data: this.transformSimulationResponse({ participants: storyData.characters }, storyData),
        timestamp: new Date().toISOString(),
      };
    } catch (_error) {
      // Fallback to original simulation API
      logger.warn(`New story generation API not available, falling back to legacy simulation: ${(_error as Error).message}`);
      
      const simulationRequest = {
        character_names: storyData.characters,
        turns: storyData.settings.turns,
        narrative_style: storyData.settings.narrativeStyle,
      };

      const response = await this.client.post<SimulationLegacyResponse>('/simulations', simulationRequest as unknown as Record<string, unknown>);
      
      return {
        success: true,
        data: this.transformSimulationResponse(response.data, storyData),
        timestamp: new Date().toISOString(),
      };
    }
  }

  async getGenerationStatus(generationId: string): Promise<{ generation_id: string; status: string; progress: number; stage: string; estimated_time_remaining: number; }> {
    const response = await this.client.get<{ generation_id: string; status: string; progress: number; stage: string; estimated_time_remaining: number; }>(`/api/v1/stories/status/${generationId}`);
    return response.data;
  }

  // Campaign APIs
  async getCampaigns(): Promise<string[]> {
    const response = await this.client.get<{ campaigns: string[] }>('/campaigns');
    return response.data.campaigns;
  }

  async createCampaign(name: string, description?: string): Promise<ApiResponse<{ id: string; name: string; description: string }>> {
    const response = await this.client.post<{ id: string; name: string; description: string }>('/campaigns', {
      campaign_name: name,
      description: description || '',
    });

    return {
      success: true,
      data: response.data,
      timestamp: new Date().toISOString(),
    };
  }

  // Helper methods for data transformation
  private transformCharacterResponse(data: CharacterDetailResponse, name: string): Character {
    return {
      id: name,
      name: data.name || name,
      faction: 'Unknown', // Extract from narrative_context if available
      role: 'Character',
      description: data.narrative_context || '',
      stats: this.extractStatsFromData(data.structured_data),
      equipment: this.extractEquipmentFromData(data.structured_data),
      relationships: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    };
  }

  private transformEnhancedCharacterResponse(data: EnhancedCharacterResponse): Character {
    const defaultStats = { strength: 5, dexterity: 5, intelligence: 5, willpower: 5, perception: 5, charisma: 5 };
    const s = (data.stats ?? {}) as Record<string, number>;
    return {
      id: data.character_id,
      name: data.name,
      faction: data.faction ?? 'Unknown',
      role: data.ai_personality?.role || 'Character',
      description: '', // Would need to combine from various sources
      stats: {
        strength: s.strength ?? defaultStats.strength,
        dexterity: s.dexterity ?? defaultStats.dexterity,
        intelligence: s.intelligence ?? defaultStats.intelligence,
        willpower: s.willpower ?? defaultStats.willpower,
        perception: s.perception ?? defaultStats.perception,
        charisma: s.charisma ?? defaultStats.charisma,
      },
      equipment: data.equipment.map((eq: { name: string; equipment_type?: string; condition?: number; properties?: unknown }, index: number) => ({
        id: `${data.character_id}_eq_${index}`,
        name: eq.name,
        type: eq.equipment_type ?? 'unknown',
        description: eq.properties ? JSON.stringify(eq.properties) : '',
        condition: eq.condition ?? 1.0,
      })),
      relationships: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    };
  }

  private transformCharacterCreationResponse(data: Record<string, unknown>, formData: CharacterFormData): Character {
    const maybeName = (data as { name?: unknown }).name;
    const nameFromServer = typeof maybeName === 'string' ? maybeName : formData.name;
    return {
      id: nameFromServer,
      name: formData.name,
      faction: formData.faction,
      role: formData.role,
      description: formData.description,
      stats: formData.stats,
      equipment: formData.equipment.map((eq, index) => ({
        ...eq,
        id: `${nameFromServer}_eq_${index}`,
      })),
      relationships: formData.relationships.map(rel => ({
        ...rel,
        targetCharacterId: '', // Would need to be set by user
      })),
      createdAt: new Date(),
      updatedAt: new Date(),
    };
  }

  private transformSimulationResponse(data: SimulationData, storyData: StoryFormData): StoryProject {
    return {
      id: `story_${Date.now()}`,
      title: storyData.title,
      description: storyData.description,
      characters: data.participants ?? storyData.characters,
      settings: storyData.settings,
      status: 'completed',
      createdAt: new Date(),
      updatedAt: new Date(),
      storyContent: data.story ?? '',
      metadata: {
        totalTurns: data.turns_executed ?? storyData.settings.turns,
        generationTime: data.duration_seconds ?? 0,
        wordCount: (data.story ?? '').split(' ').length,
        participantCount: (data.participants ?? storyData.characters).length,
        tags: [],
      },
    };
  }

  private extractStatsFromData(structuredData: CharacterStructuredData | undefined): CharacterStats {
    const defaultStats = {
      strength: 5,
      dexterity: 5,
      intelligence: 5,
      willpower: 5,
      perception: 5,
      charisma: 5,
    };

    if (!structuredData) return defaultStats;

    // Try to extract from various possible structures
    const combatStats = structuredData.combat_stats ?? {};
    const psychProfile = structuredData.psychological_profile ?? {};

    return {
      strength: combatStats.strength ?? combatStats.melee ?? defaultStats.strength,
      dexterity: combatStats.dexterity ?? combatStats.pilot ?? defaultStats.dexterity,
      intelligence: combatStats.intelligence ?? combatStats.tactics ?? defaultStats.intelligence,
      willpower: psychProfile.morale ?? psychProfile.loyalty ?? defaultStats.willpower,
      perception: combatStats.perception ?? combatStats.marksmanship ?? defaultStats.perception,
      charisma: combatStats.leadership ?? psychProfile.charisma ?? defaultStats.charisma,
    };
  }

  private extractEquipmentFromData(structuredData: CharacterStructuredData | undefined): Equipment[] {
    if (!structuredData || !structuredData.equipment) return [];

    const equipment = structuredData.equipment;
    const items: Equipment[] = [];

    // Handle different equipment structures
    if (equipment.primary_weapon) {
      items.push({
        id: 'primary_weapon',
        name: equipment.primary_weapon,
        type: 'weapon',
        description: 'Primary weapon',
        condition: 1.0,
      });
    }

    if (equipment.armor) {
      items.push({
        id: 'armor',
        name: equipment.armor,
        type: 'armor',
        description: 'Protective armor',
        condition: 1.0,
      });
    }

    if (equipment.special_gear && Array.isArray(equipment.special_gear)) {
      equipment.special_gear.forEach((item: string, index: number) => {
        items.push({
          id: `special_${index}`,
          name: item,
          type: 'special',
          description: 'Special equipment',
          condition: 1.0,
        });
      });
    }

    return items;
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
    return this.baseURL;
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


