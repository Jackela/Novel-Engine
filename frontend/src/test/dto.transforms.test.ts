import { describe, it, expect } from 'vitest';
import {
  extractStatsFromData,
  extractEquipmentFromData,
  transformCharacterResponse,
  transformEnhancedCharacterResponse,
  transformSimulationResponse
} from '../services/dtoTransforms';

describe('DTO transforms', () => {
  it('extracts default stats when structured data is missing', () => {
    const stats = extractStatsFromData(undefined);
    expect(stats).toMatchObject({
      strength: 5,
      dexterity: 5,
      intelligence: 5,
      willpower: 5,
      perception: 5,
      charisma: 5,
    });
  });

  it('extracts equipment items from structured data', () => {
    const items = extractEquipmentFromData({
      equipment: {
        primary_weapon: 'Rifle',
        armor: 'Kevlar',
        special_gear: ['Grappling Hook'],
      },
    });
    expect(items.map((i: any) => i.name)).toEqual(['Rifle', 'Kevlar', 'Grappling Hook']);
  });

  it('transforms character response with fallback fields', () => {
    const res = transformCharacterResponse({
      name: 'Aria',
      structured_data: { combat_stats: { strength: 7 } },
    }, 'Aria');
    expect(res.name).toBe('Aria');
    expect(res.stats.strength).toBe(7);
  });

  it('transforms enhanced character response with equipment and fallback role', () => {
    const res = transformEnhancedCharacterResponse({
      character_id: 'c1',
      name: 'Kael',
      faction: 'Vanguard',
      equipment: [
        { name: 'Blade', equipment_type: 'weapon', condition: 1.0 },
      ],
    });
    expect(res.id).toBe('c1');
    expect(res.name).toBe('Kael');
    expect(res.role).toBe('Character');
    expect(res.equipment[0].name).toBe('Blade');
  });

  it('transforms simulation response to StoryProject structure', () => {
    const story = transformSimulationResponse(
      { story: 'Once upon a time', turns_executed: 3, duration_seconds: 2, participants: ['Aria'] },
      { title: 'Test', description: 'Desc', characters: ['Aria'], settings: { turns: 3, narrativeStyle: 'concise', genre: 'test', tone: 'dramatic', environment: 'test', objectives: [] } }
    );
    expect(story.title).toBe('Test');
    expect(story.metadata.totalTurns).toBe(3);
    expect(story.characters).toEqual(['Aria']);
  });
});
