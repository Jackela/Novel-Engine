
import type {
    Character,
    StoryProject,
    CharacterFormData,
    StoryFormData,
    CharacterStats,
    Equipment
} from '@/types';
import type {
    CharacterDetailResponse,
    EnhancedCharacterResponse,
    CharacterStructuredData,
} from '@/types/dto';

// Default stats constant
const DEFAULT_STATS: CharacterStats = {
    strength: 5,
    dexterity: 5,
    intelligence: 5,
    willpower: 5,
    perception: 5,
    charisma: 5,
};

export function extractStatsFromData(structuredData: CharacterStructuredData | undefined): CharacterStats {
    if (!structuredData) return { ...DEFAULT_STATS };

    // Try to extract from various possible structures
    const combatStats = structuredData.combat_stats ?? {};
    const psychProfile = structuredData.psychological_profile ?? {};

    return {
        strength: combatStats.strength ?? combatStats.melee ?? DEFAULT_STATS.strength,
        dexterity: combatStats.dexterity ?? combatStats.pilot ?? DEFAULT_STATS.dexterity,
        intelligence: combatStats.intelligence ?? combatStats.tactics ?? DEFAULT_STATS.intelligence,
        willpower: psychProfile.morale ?? psychProfile.loyalty ?? DEFAULT_STATS.willpower,
        perception: combatStats.perception ?? combatStats.marksmanship ?? DEFAULT_STATS.perception,
        charisma: combatStats.leadership ?? psychProfile.charisma ?? DEFAULT_STATS.charisma,
    };
}

export function extractEquipmentFromData(structuredData: CharacterStructuredData | undefined): Equipment[] {
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

export function transformCharacterResponse(data: CharacterDetailResponse, name: string): Character {
    return {
        id: name,
        name: data.name || name,
        faction: 'Unknown', // Extract from narrative_context if available
        role: 'Character',
        description: data.narrative_context || '',
        stats: extractStatsFromData(data.structured_data),
        equipment: extractEquipmentFromData(data.structured_data),
        relationships: [],
        createdAt: new Date(),
        updatedAt: new Date(),
    };
}

export function transformEnhancedCharacterResponse(data: EnhancedCharacterResponse): Character {
    const s = (data.stats ?? {}) as Record<string, number>;
    return {
        id: data.character_id,
        name: data.name,
        faction: data.faction ?? 'Unknown',
        role: data.ai_personality?.role || 'Character',
        description: '', // Would need to combine from various sources
        stats: {
            strength: s.strength ?? DEFAULT_STATS.strength,
            dexterity: s.dexterity ?? DEFAULT_STATS.dexterity,
            intelligence: s.intelligence ?? DEFAULT_STATS.intelligence,
            willpower: s.willpower ?? DEFAULT_STATS.willpower,
            perception: s.perception ?? DEFAULT_STATS.perception,
            charisma: s.charisma ?? DEFAULT_STATS.charisma,
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

export function transformCharacterCreationResponse(data: Record<string, unknown>, formData: CharacterFormData): Character {
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

export function transformSimulationResponse(
    orchestrationData: any,
    storyData: StoryFormData
): StoryProject {
    // orchestrationData is effectively unused in the current mapping logic in api.ts
    // but we include it for future mapping. 
    // currently api.ts lines 176-196 map from storyData and static values.

    return {
        id: `story_${Date.now()}`,
        title: storyData.title,
        description: storyData.description,
        characters: storyData.characters,
        settings: storyData.settings,
        status: 'generating', // Orchestration starts in generating state
        createdAt: new Date(),
        updatedAt: new Date(),
        storyContent: '', // Content generated asynchronously
        metadata: {
            totalTurns: storyData.settings.turns || 3,
            generationTime: 0,
            wordCount: 0,
            participantCount: storyData.characters.length,
            tags: [],
        },
    };
}
