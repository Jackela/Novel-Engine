import type {
  CombatStats,
  StructuredCharacterData,
  EquipmentItem,
} from '@/types/schemas';

const defaultStats: CombatStats = {
  strength: 5,
  dexterity: 5,
  intelligence: 5,
  willpower: 5,
  perception: 5,
  charisma: 5,
};

export function extractStatsFromData(
  data?: StructuredCharacterData | null
): CombatStats {
  const partial = data?.combat_stats ?? {};
  return {
    strength: partial.strength ?? defaultStats.strength,
    dexterity: partial.dexterity ?? defaultStats.dexterity,
    intelligence: partial.intelligence ?? defaultStats.intelligence,
    willpower: partial.willpower ?? defaultStats.willpower,
    perception: partial.perception ?? defaultStats.perception,
    charisma: partial.charisma ?? defaultStats.charisma,
  };
}

export function extractEquipmentFromData(
  data?: StructuredCharacterData | null
): EquipmentItem[] {
  const equipment = data?.equipment;
  if (!equipment) {
    return [];
  }
  const items: EquipmentItem[] = [];
  if (equipment.primary_weapon) {
    items.push({
      name: equipment.primary_weapon,
      equipment_type: 'weapon',
      condition: 1,
    });
  }
  if (equipment.armor) {
    items.push({ name: equipment.armor, equipment_type: 'armor', condition: 1 });
  }
  if (equipment.special_gear?.length) {
    items.push(
      ...equipment.special_gear.map((name) => ({
        name,
        equipment_type: 'gear',
        condition: 1,
      }))
    );
  }
  return items;
}

export function transformCharacterResponse(
  response: { name?: string; structured_data?: StructuredCharacterData },
  fallbackName: string
) {
  return {
    name: response.name ?? fallbackName,
    stats: extractStatsFromData(response.structured_data),
  };
}

export function transformEnhancedCharacterResponse(response: {
  character_id: string;
  name: string;
  faction?: string;
  equipment?: EquipmentItem[];
  role?: string;
}) {
  return {
    id: response.character_id,
    name: response.name,
    faction: response.faction ?? 'Unknown',
    role: response.role ?? 'Character',
    equipment: response.equipment ?? [],
  };
}

export function transformSimulationResponse(
  simulation: {
    story: string;
    turns_executed?: number;
    duration_seconds?: number;
    participants?: string[];
  },
  request: {
    title: string;
    description?: string;
    characters?: string[];
    settings?: {
      turns?: number;
      narrativeStyle?: string;
      genre?: string;
      tone?: string;
      environment?: string;
      objectives?: string[];
    };
  }
) {
  return {
    title: request.title,
    description: request.description ?? '',
    content: simulation.story,
    metadata: {
      totalTurns: simulation.turns_executed ?? request.settings?.turns ?? 0,
      durationSeconds: simulation.duration_seconds ?? 0,
    },
    characters: request.characters ?? simulation.participants ?? [],
  };
}
