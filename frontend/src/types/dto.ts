export interface CharacterSummary {
  id: string;
  name: string;
  status: string;
  type: string;
  updated_at: string;
  workspace_id?: string | null;
}

export interface CharactersListResponse {
  characters: CharacterSummary[];
}

export interface CharacterStructuredDataEquipmentItem {
  name: string;
  type?: string;
  description?: string;
  condition?: number;
}

export type CharacterStructuredEquipment =
  | {
      primary_weapon?: string;
      armor?: string;
      special_gear?: string[];
      items?: CharacterStructuredDataEquipmentItem[];
    }
  | CharacterStructuredDataEquipmentItem[];

export interface CharacterStructuredData {
  combat_stats?: Partial<Record<'strength'|'dexterity'|'intelligence'|'willpower'|'perception'|'charisma'|'melee'|'pilot'|'tactics'|'marksmanship'|'leadership', number>>;
  psychological_profile?: Partial<Record<'morale'|'loyalty'|'charisma', number>>;
  stats?: Partial<Record<'strength'|'dexterity'|'intelligence'|'willpower'|'perception'|'charisma', number>>;
  equipment?: CharacterStructuredEquipment;
  faction?: string;
  role?: string;
}

export interface CharacterDetailResponse {
  character_id?: string;
  character_name?: string;
  background_summary?: string;
  personality_traits?: string;
  current_status?: string;
  current_location?: string;
  inventory?: string[];
  metadata?: Record<string, unknown>;
  relationships?: Record<string, number>;
  skills?: Record<string, number>;
  name?: string;
  narrative_context?: string;
  structured_data?: CharacterStructuredData;
}

export interface EnhancedCharacterEquipmentItem {
  name: string;
  equipment_type: string;
  properties?: unknown;
  condition: number;
}

export interface EnhancedCharacterResponse {
  character_id: string;
  name: string;
  faction?: string;
  ai_personality?: { role?: string };
  stats?: Record<string, number>;
  equipment: EnhancedCharacterEquipmentItem[];
}

export interface GenerateStoryResponse {
  generation_id: string;
  status: string;
  message: string;
}

export interface GenerationStatusResponse {
  generation_id: string;
  status: string;
  progress: number;
  stage: string;
  estimated_time_remaining: number;
}

export interface SimulationLegacyResponse {
  story: string;
  turns_executed: number;
  duration_seconds: number;
  participants: string[];
}
