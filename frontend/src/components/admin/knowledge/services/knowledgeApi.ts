/**
 * Knowledge Management API Service
 * 
 * TypeScript client for Knowledge Management REST API
 * 
 * Features:
 * - Type-safe API calls with TypeScript interfaces
 * - Error handling with descriptive messages
 * - Consistent request/response format
 * - Integration with Novel Engine API client
 * 
 * Constitution Compliance:
 * - Article II (Hexagonal): API client adapter for frontend
 * - Article VII (Observability): Error logging and monitoring
 */

import { apiClient } from '../../../../services/api/apiClient';

// ============================================================================
// Types & Interfaces
// ============================================================================

export enum KnowledgeType {
  WORLD_LORE = 'world_lore',
  CHARACTER_BACKGROUND = 'character_background',
  FACTION_INFO = 'faction_info',
  LOCATION_DETAILS = 'location_details',
  QUEST_DATA = 'quest_data',
  HISTORICAL_EVENT = 'historical_event',
  RULE_MECHANICS = 'rule_mechanics',
  RELATIONSHIP = 'relationship',
}

export enum AccessLevel {
  PUBLIC = 'public',
  ROLE_BASED = 'role_based',
  CHARACTER_SPECIFIC = 'character_specific',
}

export interface KnowledgeEntry {
  id: string;
  content: string;
  knowledge_type: KnowledgeType;
  owning_character_id: string | null;
  access_level: AccessLevel;
  allowed_roles: string[];
  allowed_character_ids: string[];
  created_at: string; // ISO 8601 timestamp
  updated_at: string; // ISO 8601 timestamp
  created_by: string;
}

export interface CreateKnowledgeEntryRequest {
  content: string;
  knowledge_type: KnowledgeType;
  owning_character_id?: string | null;
  access_level: AccessLevel;
  allowed_roles?: string[];
  allowed_character_ids?: string[];
}

export interface UpdateKnowledgeEntryRequest {
  content: string;
}

export interface KnowledgeEntryFilters {
  knowledge_type?: KnowledgeType;
  owning_character_id?: string;
}

// ============================================================================
// API Client
// ============================================================================

const BASE_PATH = '/api/v1/knowledge';

/**
 * Knowledge Management API Client
 * 
 * Provides CRUD operations for knowledge entries:
 * - Create new knowledge entries (FR-002)
 * - List knowledge entries with filtering
 * - Get knowledge entry by ID
 * - Update knowledge entry content (FR-003)
 * - Delete knowledge entry (FR-004)
 */
export class KnowledgeAPI {
  /**
   * Create a new knowledge entry
   * 
   * @param request - Knowledge entry creation data
   * @returns Created entry ID
   * @throws Error if creation fails
   */
  static async createEntry(request: CreateKnowledgeEntryRequest): Promise<string> {
    try {
      const response = await apiClient.post<{ entry_id: string }>(
        `${BASE_PATH}/entries`,
        request
      );
      return response.data.entry_id;
    } catch (error: any) {
      console.error('[KnowledgeAPI] Failed to create entry:', error);
      throw new Error(
        error.response?.data?.detail || 'Failed to create knowledge entry'
      );
    }
  }

  /**
   * List knowledge entries with optional filtering
   * 
   * @param filters - Optional filters for knowledge type and owning character
   * @returns Array of knowledge entries
   * @throws Error if retrieval fails
   */
  static async listEntries(filters?: KnowledgeEntryFilters): Promise<KnowledgeEntry[]> {
    try {
      const params = new URLSearchParams();
      if (filters?.knowledge_type) {
        params.append('knowledge_type', filters.knowledge_type);
      }
      if (filters?.owning_character_id) {
        params.append('owning_character_id', filters.owning_character_id);
      }

      const response = await apiClient.get<KnowledgeEntry[]>(
        `${BASE_PATH}/entries${params.toString() ? `?${params.toString()}` : ''}`
      );
      return response.data;
    } catch (error: any) {
      console.error('[KnowledgeAPI] Failed to list entries:', error);
      throw new Error(
        error.response?.data?.detail || 'Failed to retrieve knowledge entries'
      );
    }
  }

  /**
   * Get a specific knowledge entry by ID
   * 
   * @param entryId - Unique identifier of the entry
   * @returns Knowledge entry details
   * @throws Error if entry not found or retrieval fails
   */
  static async getEntry(entryId: string): Promise<KnowledgeEntry> {
    try {
      const response = await apiClient.get<KnowledgeEntry>(
        `${BASE_PATH}/entries/${entryId}`
      );
      return response.data;
    } catch (error: any) {
      console.error('[KnowledgeAPI] Failed to get entry:', error);
      if (error.response?.status === 404) {
        throw new Error('Knowledge entry not found');
      }
      throw new Error(
        error.response?.data?.detail || 'Failed to retrieve knowledge entry'
      );
    }
  }

  /**
   * Update an existing knowledge entry's content
   * 
   * @param entryId - Unique identifier of the entry
   * @param request - Update data (new content)
   * @throws Error if update fails
   */
  static async updateEntry(
    entryId: string,
    request: UpdateKnowledgeEntryRequest
  ): Promise<void> {
    try {
      await apiClient.put(
        `${BASE_PATH}/entries/${entryId}`,
        request
      );
    } catch (error: any) {
      console.error('[KnowledgeAPI] Failed to update entry:', error);
      if (error.response?.status === 404) {
        throw new Error('Knowledge entry not found');
      }
      throw new Error(
        error.response?.data?.detail || 'Failed to update knowledge entry'
      );
    }
  }

  /**
   * Delete a knowledge entry
   * 
   * @param entryId - Unique identifier of the entry
   * @throws Error if deletion fails
   */
  static async deleteEntry(entryId: string): Promise<void> {
    try {
      await apiClient.delete(`${BASE_PATH}/entries/${entryId}`);
    } catch (error: any) {
      console.error('[KnowledgeAPI] Failed to delete entry:', error);
      if (error.response?.status === 404) {
        throw new Error('Knowledge entry not found');
      }
      throw new Error(
        error.response?.data?.detail || 'Failed to delete knowledge entry'
      );
    }
  }
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Format timestamp for display
 * 
 * @param isoTimestamp - ISO 8601 timestamp string
 * @returns Human-readable date string
 */
export function formatTimestamp(isoTimestamp: string): string {
  const date = new Date(isoTimestamp);
  return date.toLocaleString();
}

/**
 * Get human-readable knowledge type label
 * 
 * @param type - Knowledge type enum value
 * @returns Formatted label
 */
export function getKnowledgeTypeLabel(type: KnowledgeType): string {
  const labels: Record<KnowledgeType, string> = {
    [KnowledgeType.WORLD_LORE]: 'World Lore',
    [KnowledgeType.CHARACTER_BACKGROUND]: 'Character Background',
    [KnowledgeType.FACTION_INFO]: 'Faction Information',
    [KnowledgeType.LOCATION_DETAILS]: 'Location Details',
    [KnowledgeType.QUEST_DATA]: 'Quest Data',
    [KnowledgeType.HISTORICAL_EVENT]: 'Historical Event',
    [KnowledgeType.RULE_MECHANICS]: 'Rule & Mechanics',
    [KnowledgeType.RELATIONSHIP]: 'Relationship',
  };
  return labels[type] || type;
}

/**
 * Get human-readable access level label
 * 
 * @param level - Access level enum value
 * @returns Formatted label
 */
export function getAccessLevelLabel(level: AccessLevel): string {
  const labels: Record<AccessLevel, string> = {
    [AccessLevel.PUBLIC]: 'Public (All Agents)',
    [AccessLevel.ROLE_BASED]: 'Role-Based',
    [AccessLevel.CHARACTER_SPECIFIC]: 'Character-Specific',
  };
  return labels[level] || level;
}
