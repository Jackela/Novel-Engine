// Novel Engine API Service
// Centralized API communication layer

import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { 
  Character, 
  StoryProject, 
  GenerationSession, 
  SystemStatus,
  ApiResponse,
  PaginatedResponse,
  CharacterFormData,
  StoryFormData,
  ExportOptions
} from '../types';

class NovelEngineAPI {
  private client: AxiosInstance;
  private baseURL: string;

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
        console.log(`🌐 API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        console.error('❌ API Request Error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => {
        console.log(`✅ API Response: ${response.status} ${response.config.url}`);
        return response;
      },
      (error) => {
        console.error('❌ API Response Error:', error.response?.data || error.message);
        return Promise.reject(this.handleError(error));
      }
    );
  }

  private handleError(error: any): Error {
    if (error.response) {
      // Server responded with error status
      const message = error.response.data?.detail || error.response.data?.message || 'Server error';
      return new Error(`API Error (${error.response.status}): ${message}`);
    } else if (error.request) {
      // Network error
      return new Error('Network error: Unable to connect to server');
    } else {
      // Other error
      return new Error(`Request error: ${error.message}`);
    }
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

  // Character APIs
  async getCharacters(): Promise<string[]> {
    const response = await this.client.get<{ characters: string[] }>('/characters');
    return response.data.characters;
  }

  async getCharacterDetails(name: string): Promise<Character> {
    const response = await this.client.get<any>(`/characters/${encodeURIComponent(name)}`);
    return this.transformCharacterResponse(response.data, name);
  }

  async getEnhancedCharacterData(name: string): Promise<Character> {
    try {
      const response = await this.client.get<any>(`/characters/${encodeURIComponent(name)}/enhanced`);
      return this.transformEnhancedCharacterResponse(response.data);
    } catch (error) {
      // Fallback to regular character details
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

    const response = await this.client.post<any>('/characters', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return {
      success: true,
      data: this.transformCharacterCreationResponse(response.data, characterData),
      timestamp: new Date().toISOString(),
    };
  }

  // Story and Simulation APIs
  async runSimulation(storyData: StoryFormData): Promise<ApiResponse<StoryProject>> {
    const simulationRequest = {
      character_names: storyData.characters,
      turns: storyData.settings.turns,
      narrative_style: storyData.settings.narrativeStyle,
    };

    const response = await this.client.post<any>('/simulations', simulationRequest);
    
    return {
      success: true,
      data: this.transformSimulationResponse(response.data, storyData),
      timestamp: new Date().toISOString(),
    };
  }

  // Campaign APIs
  async getCampaigns(): Promise<string[]> {
    const response = await this.client.get<{ campaigns: string[] }>('/campaigns');
    return response.data.campaigns;
  }

  async createCampaign(name: string, description?: string): Promise<ApiResponse<any>> {
    const response = await this.client.post<any>('/campaigns', {
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
  private transformCharacterResponse(data: any, name: string): Character {
    return {
      id: name,
      name: data.character_name || name,
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

  private transformEnhancedCharacterResponse(data: any): Character {
    return {
      id: data.character_id,
      name: data.name,
      faction: data.faction,
      role: data.ai_personality?.role || 'Character',
      description: '', // Would need to combine from various sources
      stats: data.stats,
      equipment: data.equipment.map((eq: any, index: number) => ({
        id: `${data.character_id}_eq_${index}`,
        name: eq.name,
        type: eq.equipment_type,
        description: eq.properties ? JSON.stringify(eq.properties) : '',
        condition: eq.condition,
      })),
      relationships: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    };
  }

  private transformCharacterCreationResponse(data: any, formData: CharacterFormData): Character {
    return {
      id: data.name,
      name: formData.name,
      faction: formData.faction,
      role: formData.role,
      description: formData.description,
      stats: formData.stats,
      equipment: formData.equipment.map((eq, index) => ({
        ...eq,
        id: `${data.name}_eq_${index}`,
      })),
      relationships: formData.relationships.map(rel => ({
        ...rel,
        targetCharacterId: '', // Would need to be set by user
      })),
      createdAt: new Date(),
      updatedAt: new Date(),
    };
  }

  private transformSimulationResponse(data: any, storyData: StoryFormData): StoryProject {
    return {
      id: `story_${Date.now()}`,
      title: storyData.title,
      description: storyData.description,
      characters: data.participants,
      settings: storyData.settings,
      status: 'completed',
      createdAt: new Date(),
      updatedAt: new Date(),
      storyContent: data.story,
      metadata: {
        totalTurns: data.turns_executed,
        generationTime: data.duration_seconds,
        wordCount: data.story.split(' ').length,
        participantCount: data.participants.length,
        tags: [],
      },
    };
  }

  private extractStatsFromData(structuredData: any): any {
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
    const combatStats = structuredData.combat_stats || {};
    const psychProfile = structuredData.psychological_profile || {};

    return {
      strength: combatStats.strength || combatStats.melee || defaultStats.strength,
      dexterity: combatStats.dexterity || combatStats.pilot || defaultStats.dexterity,
      intelligence: combatStats.intelligence || combatStats.tactics || defaultStats.intelligence,
      willpower: psychProfile.morale || psychProfile.loyalty || defaultStats.willpower,
      perception: combatStats.perception || combatStats.marksmanship || defaultStats.perception,
      charisma: combatStats.leadership || psychProfile.charisma || defaultStats.charisma,
    };
  }

  private extractEquipmentFromData(structuredData: any): any[] {
    if (!structuredData || !structuredData.equipment) return [];

    const equipment = structuredData.equipment;
    const items = [];

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

  // Utility methods
  async testConnection(): Promise<boolean> {
    try {
      await this.getHealth();
      return true;
    } catch (error) {
      console.error('Connection test failed:', error);
      return false;
    }
  }

  getBaseURL(): string {
    return this.baseURL;
  }

  // Export functionality (to be implemented)
  async exportStory(projectId: string, options: ExportOptions): Promise<Blob> {
    // This would integrate with a future export endpoint
    throw new Error('Export functionality not yet implemented');
  }
}

// Create and export singleton instance
export const api = new NovelEngineAPI();
export default api;