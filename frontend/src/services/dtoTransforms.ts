type CombatStats = {
  strength: number;
  dexterity: number;
  intelligence: number;
  willpower: number;
  perception: number;
  charisma: number;
};

const defaultStats: CombatStats = {
  strength: 5,
  dexterity: 5,
  intelligence: 5,
  willpower: 5,
  perception: 5,
  charisma: 5,
};

type StructuredCharacterData = {
  combat_stats?: Partial<CombatStats>;
  equipment?: {
    primary_weapon?: string;
    armor?: string;
    special_gear?: string[];
  };
};

type EquipmentItem = {
  name: string;
  equipment_type?: string;
  condition?: number;
};

export function extractStatsFromData(
  data?: StructuredCharacterData | null
): CombatStats {
  const stats = data?.combat_stats ?? {};
  return { ...defaultStats, ...stats };
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
