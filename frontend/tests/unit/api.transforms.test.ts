import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { CharacterDetailResponse, EnhancedCharacterResponse } from '@/types/dto';

let handlers: { getImpl: (...args: any[]) => any; postImpl?: (...args: any[]) => any } = {
  getImpl: () => Promise.resolve({ data: {} }),
};
vi.mock('axios', () => {
  const client = {
    get: (...args: any[]) => handlers.getImpl(...args),
    post: (...args: any[]) => (handlers.postImpl ? handlers.postImpl(...args) : Promise.resolve({ data: {} })),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  };
  return {
    default: { create: vi.fn(() => client) },
    AxiosInstance: class {},
    __setHandlers: (h: typeof handlers) => { handlers = h; },
  };
});

import api from '@/services/api';

beforeEach(() => {
  handlers = { getImpl: () => Promise.resolve({ data: {} }) };
});

describe('DTO transforms', () => {
  it('maps CharacterDetailResponse to domain Character', async () => {
    const dto: CharacterDetailResponse = {
      name: 'rhea_valkyr',
      narrative_context: 'Elite pilot from the Alliance Network',
      structured_data: {
        combat_stats: { strength: 7, dexterity: 9, marksmanship: 8 },
        psychological_profile: { morale: 8, loyalty: 9 },
        equipment: { primary_weapon: 'Pulse Rifle', armor: 'Aegis Suit', special_gear: ['Jetpack'] },
      },
    };
    const axiosMod: any = await import('axios');
    axiosMod.__setHandlers({ getImpl: vi.fn().mockResolvedValueOnce({ data: dto }) });

    const result = await api.getCharacterDetails('rhea_valkyr');
    expect(result.id).toBe('rhea_valkyr');
    expect(result.name).toBe('rhea_valkyr');
    expect(result.description).toContain('Alliance Network');
    expect(result.stats.strength).toBe(7);
    expect(result.stats.dexterity).toBe(9);
    expect(result.stats.perception).toBeDefined();
    expect(result.equipment.length).toBeGreaterThan(0);
  });

  it('maps EnhancedCharacterResponse to domain Character', async () => {
    const dto: EnhancedCharacterResponse = {
      character_id: 'char_001',
      name: 'Kade Ardent',
      faction: 'Alliance Network',
      ai_personality: { role: 'Sentinel' },
      stats: { strength: 6, intelligence: 7 },
      equipment: [
        { name: 'Arc Blade', equipment_type: 'weapon', condition: 0.9 },
        { name: 'Shield Emitter', equipment_type: 'special', condition: 1.0 },
      ],
    } as any;
    const axiosMod2: any = await import('axios');
    axiosMod2.__setHandlers({ getImpl: vi.fn().mockResolvedValueOnce({ data: dto }) });

    const result = await api.getEnhancedCharacterData('Kade Ardent');
    expect(result.id).toBe('char_001');
    expect(result.name).toBe('Kade Ardent');
    expect(result.role).toBe('Sentinel');
    expect(result.equipment[0].name).toBe('Arc Blade');
  });
});
