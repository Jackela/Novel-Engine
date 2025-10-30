export interface CharactersListResponse {
  characters: string[];
}

export interface CharacterStructuredData {
  combat_stats?: Partial<Record<'strength'|'dexterity'|'intelligence'|'willpower'|'perception'|'charisma'|'melee'|'pilot'|'tactics'|'marksmanship'|'leadership', number>>;
  psychological_profile?: Partial<Record<'morale'|'loyalty'|'charisma', number>>;
  equipment?: {
    primary_weapon?: string;
    armor?: string;
    special_gear?: string[];
  };
}

export interface CharacterDetailResponse {
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

