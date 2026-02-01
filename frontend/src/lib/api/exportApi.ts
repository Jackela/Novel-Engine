/**
 * Character Export API client functions.
 *
 * Provides functions for exporting character data including
 * the full character graph with relationships.
 */
import { api } from './client';
import {
  RelationshipListResponseSchema,
  type RelationshipListResponse,
  type CharacterDetail,
  type RelationshipResponse,
} from '@/types/schemas';

/**
 * Fetch all relationships for a specific character.
 *
 * @param characterId - The character's agent_id or character_id.
 * @returns List of relationships where the character is source or target.
 */
export async function getCharacterRelationships(
  characterId: string
): Promise<RelationshipListResponse> {
  const response = await api.get<unknown>(`/relationships/by-entity/${characterId}`);
  return RelationshipListResponseSchema.parse(response);
}

/**
 * Character export data structure.
 * Contains all character information plus their relationship graph.
 */
export interface CharacterExportData {
  export_version: string;
  exported_at: string;
  character: CharacterDetail;
  relationships: RelationshipResponse[];
}

/**
 * Build the complete character export data object.
 *
 * @param character - The full character detail object.
 * @param relationships - List of relationships involving this character.
 * @returns Complete export data structure.
 */
export function buildCharacterExportData(
  character: CharacterDetail,
  relationships: RelationshipResponse[]
): CharacterExportData {
  return {
    export_version: '1.0.0',
    exported_at: new Date().toISOString(),
    character,
    relationships,
  };
}

/**
 * Trigger a JSON file download in the browser.
 *
 * @param data - The data object to export as JSON.
 * @param filename - The filename for the download (without extension).
 */
export function downloadAsJson(data: unknown, filename: string): void {
  const jsonString = JSON.stringify(data, null, 2);
  const blob = new Blob([jsonString], { type: 'application/json' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = `${filename}.json`;
  document.body.appendChild(link);
  link.click();

  // Cleanup
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
