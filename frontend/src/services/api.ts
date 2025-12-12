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
} from '@/types';
import type {
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
    return transformCharacterResponse(response.data, name);
  }

  async getEnhancedCharacterData(name: string): Promise<Character> {
    try {
      const response = await this.client.get<EnhancedCharacterResponse>(`/characters/${encodeURIComponent(name)}/enhanced`);
      return transformEnhancedCharacterResponse(response.data);
    } catch (error) {
      logger.warn(`Enhanced character data failed for ${name}, falling back: ${(error as Error).message}`);
      return this.getCharacterDetails(name);
    }
  }

  async createCharacter(characterData: CharacterFormData, files?: File[]): Promise<ApiResponse<Character>> {
    const formData = new FormData();
    formData.append('name', characterData.name);
    formData.append('description', characterData.description);
    formData.append('faction', characterData.faction);
    formData.append('role', characterData.role);
    formData.append('stats', JSON.stringify(characterData.stats));
    formData.append('equipment', JSON.stringify(characterData.equipment));

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

    const character = transformCharacterCreationResponse(response.data as Record<string, unknown>, characterData);

    // Client caches managed by consumers (e.g., React Query). No internal cache.

    return {
      success: true,
      data: character,
      timestamp: new Date().toISOString(),
    };
  }

  // Story and Simulation APIs
  async runSimulation(storyData: StoryFormData): Promise<ApiResponse<StoryProject> & { generation_id?: string }> {
    const orchestrationRequest = {
      character_names: storyData.characters,
      total_turns: storyData.settings.turns || 3,
      start_turn: 1
    };

    // Call the orchestration start endpoint
    const response = await this.client.post<any>('/api/orchestration/start', orchestrationRequest);

    const storyProject = transformSimulationResponse(response.data.data, storyData);

    return {
      success: response.data.success,
      generation_id: 'orchestration_active', // Singleton state, so ID is static/irrelevant
      data: storyProject,
      timestamp: new Date().toISOString(),
    };
  }

  async getGenerationStatus(generationId: string): Promise<{ generation_id: string; status: string; progress: number; stage: string; estimated_time_remaining: number; }> {
    const response = await this.client.get<{ generation_id: string; status: string; progress: number; stage: string; estimated_time_remaining: number; }>(`/api/stories/status/${generationId}`);
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


