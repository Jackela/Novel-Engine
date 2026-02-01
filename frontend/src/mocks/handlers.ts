import { http, HttpResponse, delay } from 'msw';
import type { CharacterDetail, CharacterSummary } from '@/shared/types/character';
import {
  CharactersListResponseSchema,
  OrchestrationStartRequestSchema,
  type RelationshipResponse,
  type WorldLocation,
  type ItemResponse,
} from '@/types/schemas';

const API_PREFIX = '/api';

const nowIso = () => new Date().toISOString();

const characterSummaries: CharacterSummary[] = [
  {
    id: 'aria-shadowbane',
    agent_id: 'aria-shadowbane',
    name: 'Aria Shadowbane',
    status: 'active',
    type: 'protagonist',
    updated_at: nowIso(),
    workspace_id: 'guest-workspace',
    aliases: ['The Shadow'],
    archetype: 'Tactician',
    traits: ['Strategic', 'Resilient', 'Decisive'],
    appearance: 'Tall with dark hair and piercing eyes',
  },
  {
    id: 'merchant-aldric',
    agent_id: 'merchant-aldric',
    name: 'Merchant Aldric',
    status: 'active',
    type: 'npc',
    updated_at: nowIso(),
    workspace_id: 'guest-workspace',
    aliases: [],
    archetype: 'Merchant',
    traits: ['Shrewd', 'Friendly'],
    appearance: null,
  },
];

const characterDetails: CharacterDetail[] = [
  {
    agent_id: 'aria-shadowbane',
    character_id: 'aria-shadowbane',
    character_name: 'Aria Shadowbane',
    name: 'Aria Shadowbane',
    background_summary: 'A tactician navigating a fractured realm.',
    personality_traits: 'Strategic, resilient, decisive.',
    current_status: 'active',
    narrative_context: '',
    skills: { tactics: 0.8, leadership: 0.7 },
    relationships: {},
    current_location: 'Meridian Station',
    inventory: [],
    metadata: {},
    structured_data: {},
  },
  {
    agent_id: 'merchant-aldric',
    character_id: 'merchant-aldric',
    character_name: 'Merchant Aldric',
    name: 'Merchant Aldric',
    background_summary: 'A seasoned trader with a hidden agenda.',
    personality_traits: 'Connected, observant, cautious.',
    current_status: 'active',
    narrative_context: '',
    skills: { negotiation: 0.7 },
    relationships: {},
    current_location: 'Trade Hub',
    inventory: [],
    metadata: {},
    structured_data: {},
  },
];

// Mock relationships for the graph visualization
const mockRelationships: RelationshipResponse[] = [
  {
    id: 'rel-001',
    source_id: 'aria-shadowbane',
    source_type: 'character',
    target_id: 'merchant-aldric',
    target_type: 'character',
    relationship_type: 'ally',
    description: 'Trusted business partner and information source',
    strength: 75,
    is_active: true,
    created_at: nowIso(),
    updated_at: nowIso(),
  },
  {
    id: 'rel-002',
    source_id: 'aria-shadowbane',
    source_type: 'character',
    target_id: 'lord-vexar',
    target_type: 'character',
    relationship_type: 'enemy',
    description: 'Long-standing rivalry over territorial control',
    strength: 90,
    is_active: true,
    created_at: nowIso(),
    updated_at: nowIso(),
  },
  {
    id: 'rel-003',
    source_id: 'merchant-aldric',
    source_type: 'character',
    target_id: 'lord-vexar',
    target_type: 'character',
    relationship_type: 'rival',
    description: 'Competing for trade route dominance',
    strength: 60,
    is_active: true,
    created_at: nowIso(),
    updated_at: nowIso(),
  },
  {
    id: 'rel-004',
    source_id: 'finn-bard',
    source_type: 'character',
    target_id: 'aria-shadowbane',
    target_type: 'character',
    relationship_type: 'mentor',
    description: 'Trained Aria in diplomacy and negotiation',
    strength: 85,
    is_active: true,
    created_at: nowIso(),
    updated_at: nowIso(),
  },
  {
    id: 'rel-005',
    source_id: 'finn-bard',
    source_type: 'character',
    target_id: 'merchant-aldric',
    target_type: 'character',
    relationship_type: 'family',
    description: 'Distant cousins through maternal lineage',
    strength: 50,
    is_active: true,
    created_at: nowIso(),
    updated_at: nowIso(),
  },
];

// Add additional mock characters for the graph
const additionalCharacterSummaries: CharacterSummary[] = [
  {
    id: 'lord-vexar',
    agent_id: 'lord-vexar',
    name: 'Lord Vexar',
    status: 'active',
    type: 'antagonist',
    updated_at: nowIso(),
    workspace_id: 'guest-workspace',
    aliases: ['The Dark Prince'],
    archetype: 'Antagonist',
    traits: ['Cunning', 'Ambitious', 'Ruthless'],
    appearance: 'Pale complexion with silver hair and cold grey eyes',
  },
  {
    id: 'finn-bard',
    agent_id: 'finn-bard',
    name: 'Finn the Bard',
    status: 'active',
    type: 'npc',
    updated_at: nowIso(),
    workspace_id: 'guest-workspace',
    aliases: ['The Wandering Minstrel'],
    archetype: 'Mentor',
    traits: ['Wise', 'Musical', 'Mysterious'],
    appearance: 'An elderly man with a warm smile and a worn lute',
  },
];

// Merge additional characters into the main array
characterSummaries.push(...additionalCharacterSummaries);

// Mock locations with 3-level hierarchy for LocationTree testing
const mockLocations: WorldLocation[] = [
  // Root: Continent
  {
    id: 'loc-continent-eldara',
    name: 'Eldara Continent',
    description: 'A vast landmass spanning temperate to arctic regions.',
    location_type: 'continent',
    population: 15000000,
    controlling_faction_id: null,
    notable_features: ['Great Mountain Range', 'Endless Forests'],
    danger_level: 'low',
    parent_location_id: null,
    child_location_ids: ['loc-region-heartlands', 'loc-region-frostpeaks'],
  },
  // Level 2: Regions
  {
    id: 'loc-region-heartlands',
    name: 'The Heartlands',
    description: 'Fertile plains with numerous settlements.',
    location_type: 'region',
    population: 5000000,
    controlling_faction_id: null,
    notable_features: ['River Valley', 'Golden Fields'],
    danger_level: 'low',
    parent_location_id: 'loc-continent-eldara',
    child_location_ids: ['loc-city-meridian', 'loc-town-crossroads'],
  },
  {
    id: 'loc-region-frostpeaks',
    name: 'Frostpeak Mountains',
    description: 'Treacherous mountain range with ancient ruins.',
    location_type: 'mountain',
    population: 50000,
    controlling_faction_id: null,
    notable_features: ['Frozen Waterfalls', 'Ancient Dwarf Mines'],
    danger_level: 'high',
    parent_location_id: 'loc-continent-eldara',
    child_location_ids: ['loc-fortress-ironhold', 'loc-dungeon-depths'],
  },
  // Level 3: Cities/Towns/Fortresses
  {
    id: 'loc-city-meridian',
    name: 'Meridian City',
    description: 'The capital and largest trading hub.',
    location_type: 'capital',
    population: 500000,
    controlling_faction_id: null,
    notable_features: ['Grand Market', 'Royal Palace', 'Mage Academy'],
    danger_level: 'low',
    parent_location_id: 'loc-region-heartlands',
    child_location_ids: [],
  },
  {
    id: 'loc-town-crossroads',
    name: 'Crossroads Town',
    description: 'A bustling town at the junction of major trade routes.',
    location_type: 'town',
    population: 15000,
    controlling_faction_id: null,
    notable_features: ['Four Winds Inn', 'Weekly Market'],
    danger_level: 'low',
    parent_location_id: 'loc-region-heartlands',
    child_location_ids: [],
  },
  {
    id: 'loc-fortress-ironhold',
    name: 'Ironhold Fortress',
    description: 'An ancient dwarven stronghold carved into the mountain.',
    location_type: 'fortress',
    population: 5000,
    controlling_faction_id: null,
    notable_features: ['Great Forge', 'Deep Mines'],
    danger_level: 'medium',
    parent_location_id: 'loc-region-frostpeaks',
    child_location_ids: [],
  },
  {
    id: 'loc-dungeon-depths',
    name: 'The Frozen Depths',
    description: 'A vast underground complex filled with ancient horrors.',
    location_type: 'dungeon',
    population: 0,
    controlling_faction_id: null,
    notable_features: ['Ice Caverns', 'Lost Treasures'],
    danger_level: 'extreme',
    parent_location_id: 'loc-region-frostpeaks',
    child_location_ids: [],
  },
  // Additional standalone location (forest)
  {
    id: 'loc-forest-whisper',
    name: 'Whisperwood Forest',
    description: 'An ancient forest filled with fey creatures.',
    location_type: 'forest',
    population: 1000,
    controlling_faction_id: null,
    notable_features: ['Fairy Circles', 'Talking Trees'],
    danger_level: 'medium',
    parent_location_id: null,
    child_location_ids: ['loc-temple-moonlight'],
  },
  {
    id: 'loc-temple-moonlight',
    name: 'Temple of Moonlight',
    description: 'A sacred elven temple hidden deep in the forest.',
    location_type: 'temple',
    population: 50,
    controlling_faction_id: null,
    notable_features: ['Lunar Altar', 'Ancient Library'],
    danger_level: 'low',
    parent_location_id: 'loc-forest-whisper',
    child_location_ids: [],
  },
];

// Mock items for inventory testing
const mockItems: ItemResponse[] = [
  {
    id: 'item-001',
    name: 'Starfall Blade',
    item_type: 'weapon',
    description: 'A legendary sword forged from a fallen star.',
    rarity: 'legendary',
    weight: 3.5,
    value: 10000,
    is_equippable: true,
    is_consumable: false,
    effects: ['+20 Attack', 'Glow in darkness'],
    lore: 'Said to have been wielded by the first king of Eldara.',
    created_at: nowIso(),
    updated_at: nowIso(),
  },
  {
    id: 'item-002',
    name: 'Leather Armor',
    item_type: 'armor',
    description: 'Standard leather armor providing basic protection.',
    rarity: 'common',
    weight: 8,
    value: 50,
    is_equippable: true,
    is_consumable: false,
    effects: ['+5 Defense'],
    lore: '',
    created_at: nowIso(),
    updated_at: nowIso(),
  },
  {
    id: 'item-003',
    name: 'Health Potion',
    item_type: 'consumable',
    description: 'Restores 50 health points when consumed.',
    rarity: 'common',
    weight: 0.5,
    value: 25,
    is_equippable: false,
    is_consumable: true,
    effects: ['Restore 50 HP'],
    lore: '',
    created_at: nowIso(),
    updated_at: nowIso(),
  },
  {
    id: 'item-004',
    name: 'Moonstone Amulet',
    item_type: 'key_item',
    description: 'An amulet required to enter the Temple of Moonlight.',
    rarity: 'rare',
    weight: 0.2,
    value: null,
    is_equippable: false,
    is_consumable: false,
    effects: [],
    lore: 'Given only to those deemed worthy by the elven priests.',
    created_at: nowIso(),
    updated_at: nowIso(),
  },
  {
    id: 'item-005',
    name: 'Iron Shield',
    item_type: 'armor',
    description: 'A sturdy iron shield.',
    rarity: 'uncommon',
    weight: 12,
    value: 150,
    is_equippable: true,
    is_consumable: false,
    effects: ['+10 Defense', 'Block chance +5%'],
    lore: '',
    created_at: nowIso(),
    updated_at: nowIso(),
  },
  {
    id: 'item-006',
    name: 'Rusty Dagger',
    item_type: 'weapon',
    description: 'An old rusty dagger. Not very effective.',
    rarity: 'common',
    weight: 0.3,
    value: 5,
    is_equippable: true,
    is_consumable: false,
    effects: ['+2 Attack'],
    lore: '',
    created_at: nowIso(),
    updated_at: nowIso(),
  },
  {
    id: 'item-007',
    name: 'Mana Crystal',
    item_type: 'consumable',
    description: 'Restores 30 mana points when consumed.',
    rarity: 'uncommon',
    weight: 0.3,
    value: 40,
    is_equippable: false,
    is_consumable: true,
    effects: ['Restore 30 MP'],
    lore: '',
    created_at: nowIso(),
    updated_at: nowIso(),
  },
  {
    id: 'item-008',
    name: 'Traveler\'s Pack',
    item_type: 'misc',
    description: 'A simple backpack for carrying supplies.',
    rarity: 'common',
    weight: 1,
    value: 10,
    is_equippable: false,
    is_consumable: false,
    effects: [],
    lore: '',
    created_at: nowIso(),
    updated_at: nowIso(),
  },
];

// Track which items are in which character's inventory
const characterInventories: Record<string, string[]> = {
  'aria-shadowbane': ['item-001', 'item-004'],
  'merchant-aldric': ['item-002', 'item-003', 'item-008'],
};

let orchestrationState = {
  status: 'idle',
  current_turn: 0,
  total_turns: 0,
  queue_length: 0,
  average_processing_time: 0,
  steps: [] as Array<{ id: string; name: string; status: string; progress: number }>,
};

const orchestrationSteps = [
  { id: 'context_gathering', name: 'Context Gathering' },
  { id: 'planning', name: 'Planning' },
  { id: 'execution', name: 'Execution' },
  { id: 'synthesis', name: 'Synthesis' },
  { id: 'output', name: 'Output' },
];

const withLatency = async () => {
  await delay(120);
};

const asObject = (body: unknown): Record<string, unknown> =>
  typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};

const stringField = (body: Record<string, unknown>, key: string, fallback = '') =>
  key in body ? String(body[key] ?? fallback) : fallback;

const recordField = <T extends Record<string, number> | Record<string, unknown>>(
  body: Record<string, unknown>,
  key: string,
  fallback: T
) =>
  key in body && typeof body[key] === 'object' && body[key] !== null
    ? (body[key] as T)
    : fallback;

const arrayField = (body: Record<string, unknown>, key: string, fallback: string[]) =>
  Array.isArray(body[key]) ? (body[key] as string[]) : fallback;

const buildLoginResponse = (email: string) => ({
  access_token: 'mock-access-token',
  refresh_token: 'mock-refresh-token',
  token_type: 'Bearer',
  expires_in: 3600,
  refresh_expires_in: 86400,
  user: {
    id: 'user-001',
    username: email.split('@')[0] || 'operator',
    email,
    roles: ['operator'],
  },
});

const buildCharacterDetail = (body: Record<string, unknown>) => {
  const agentId = stringField(body, 'agent_id');
  const name = stringField(body, 'name', agentId);
  const character_id = agentId || name.toLowerCase().replace(/\s+/g, '-');

  return {
    character_id,
    detail: {
      agent_id: character_id,
      character_id,
      character_name: name,
      name,
      background_summary: stringField(body, 'background_summary'),
      personality_traits: stringField(body, 'personality_traits'),
      current_status: 'active',
      narrative_context: '',
      skills: recordField(body, 'skills', {}),
      relationships: recordField(body, 'relationships', {}),
      current_location: stringField(body, 'current_location'),
      inventory: arrayField(body, 'inventory', []),
      metadata: recordField(body, 'metadata', {}),
      structured_data: recordField(body, 'structured_data', {}),
    } as CharacterDetail,
  };
};

export const handlers = [
  http.post(`${API_PREFIX}/auth/login`, async ({ request }) => {
    await withLatency();
    const body = asObject(await request.json().catch(() => ({})));
    const email = stringField(body, 'email', 'operator@novel.engine');
    return HttpResponse.json(buildLoginResponse(email));
  }),

  http.post(`${API_PREFIX}/auth/logout`, async () => {
    await withLatency();
    return HttpResponse.json({ success: true });
  }),

  http.post(`${API_PREFIX}/auth/refresh`, async () => {
    await withLatency();
    return HttpResponse.json(buildLoginResponse('operator@novel.engine'));
  }),

  http.post(`${API_PREFIX}/guest/sessions`, async () => {
    await withLatency();
    return HttpResponse.json({ workspace_id: 'guest-workspace' });
  }),

  http.get(`${API_PREFIX}/orchestration/status`, async () => {
    await withLatency();
    return HttpResponse.json({ success: true, data: orchestrationState });
  }),

  http.post(`${API_PREFIX}/orchestration/start`, async ({ request }) => {
    await withLatency();
    const body = await request.json().catch(() => ({}));
    const parsed = OrchestrationStartRequestSchema.safeParse(body);
    const turns = parsed.success ? (parsed.data.total_turns ?? 3) : 3;

    orchestrationState = {
      status: 'running',
      current_turn: orchestrationState.current_turn + 1,
      total_turns: turns,
      queue_length: 0,
      average_processing_time: 2.4,
      steps: orchestrationSteps.map((step, index) => ({
        id: step.id,
        name: step.name,
        status: index === 0 ? 'processing' : 'queued',
        progress: index === 0 ? 25 : 0,
      })),
    };

    return HttpResponse.json({ success: true, data: orchestrationState });
  }),

  http.post(`${API_PREFIX}/orchestration/pause`, async () => {
    await withLatency();
    orchestrationState = { ...orchestrationState, status: 'paused' };
    return HttpResponse.json({ success: true, data: orchestrationState });
  }),

  http.post(`${API_PREFIX}/orchestration/stop`, async () => {
    await withLatency();
    orchestrationState = { ...orchestrationState, status: 'idle', steps: [] };
    return HttpResponse.json({ success: true, data: orchestrationState });
  }),

  http.get(`${API_PREFIX}/orchestration/narrative`, async () => {
    await withLatency();
    return HttpResponse.json({
      success: true,
      data: {
        story: 'Mock narrative output generated for Weaver sessions.',
        participants: characterSummaries.map((character) => character.name),
        turns_completed: orchestrationState.current_turn,
        last_generated: nowIso(),
        has_content: true,
      },
    });
  }),

  http.get(`${API_PREFIX}/characters`, async () => {
    await withLatency();
    return HttpResponse.json(
      CharactersListResponseSchema.parse({ characters: characterSummaries })
    );
  }),

  http.get(`${API_PREFIX}/characters/:id`, async ({ params }) => {
    await withLatency();
    const character = characterDetails.find((item) => item.character_id === params.id);
    if (!character) {
      return HttpResponse.json({ detail: 'Character not found' }, { status: 404 });
    }
    return HttpResponse.json(character);
  }),

  http.post(`${API_PREFIX}/characters`, async ({ request }) => {
    await withLatency();
    const body = asObject(await request.json().catch(() => ({})));
    const { character_id, detail } = buildCharacterDetail(body);
    characterDetails.unshift(detail);
    characterSummaries.unshift({
      id: character_id,
      agent_id: character_id,
      name: detail.name,
      status: 'active',
      type: 'npc',
      updated_at: nowIso(),
      workspace_id: 'guest-workspace',
      aliases: [],
      archetype: null,
      traits: [],
      appearance: null,
    });
    return HttpResponse.json(detail, { status: 201 });
  }),

  http.put(`${API_PREFIX}/characters/:id`, async ({ params, request }) => {
    await withLatency();
    const index = characterDetails.findIndex((item) => item.character_id === params.id);
    if (index === -1) {
      return HttpResponse.json({ detail: 'Character not found' }, { status: 404 });
    }
    const body = asObject(await request.json().catch(() => ({})));
    const current = characterDetails[index];
    if (!current) {
      return HttpResponse.json({ detail: 'Character not found' }, { status: 404 });
    }
    const updated: CharacterDetail = {
      ...current,
      name: stringField(body, 'name', current.name),
      background_summary: stringField(
        body,
        'background_summary',
        current.background_summary
      ),
      personality_traits: stringField(
        body,
        'personality_traits',
        current.personality_traits
      ),
      skills: recordField(body, 'skills', current.skills),
      relationships: recordField(body, 'relationships', current.relationships),
      current_location: stringField(body, 'current_location', current.current_location),
      inventory: arrayField(body, 'inventory', current.inventory),
      metadata: recordField(body, 'metadata', current.metadata),
      structured_data: recordField(body, 'structured_data', current.structured_data),
    };
    characterDetails[index] = updated;
    const summaryIndex = characterSummaries.findIndex((item) => item.id === params.id);
    if (summaryIndex !== -1) {
      const summary = characterSummaries[summaryIndex];
      if (summary) {
        characterSummaries[summaryIndex] = {
          ...summary,
          name: updated.name,
          updated_at: nowIso(),
        };
      }
    }
    return HttpResponse.json(updated);
  }),

  http.delete(`${API_PREFIX}/characters/:id`, async ({ params }) => {
    await withLatency();
    const index = characterDetails.findIndex((item) => item.character_id === params.id);
    if (index === -1) {
      return HttpResponse.json({ detail: 'Character not found' }, { status: 404 });
    }
    characterDetails.splice(index, 1);
    const summaryIndex = characterSummaries.findIndex((item) => item.id === params.id);
    if (summaryIndex !== -1) {
      characterSummaries.splice(summaryIndex, 1);
    }
    return HttpResponse.json({ success: true });
  }),

  // === Relationships API ===

  http.get(`${API_PREFIX}/relationships`, async () => {
    await withLatency();
    return HttpResponse.json({
      relationships: mockRelationships,
      total: mockRelationships.length,
    });
  }),

  http.get(`${API_PREFIX}/relationships/by-entity/:entityId`, async ({ params }) => {
    await withLatency();
    const entityId = params.entityId as string;
    const filtered = mockRelationships.filter(
      (r) => r.source_id === entityId || r.target_id === entityId
    );
    return HttpResponse.json({
      relationships: filtered,
      total: filtered.length,
    });
  }),

  http.get(`${API_PREFIX}/relationships/:id`, async ({ params }) => {
    await withLatency();
    const relationship = mockRelationships.find((r) => r.id === params.id);
    if (!relationship) {
      return HttpResponse.json({ detail: 'Relationship not found' }, { status: 404 });
    }
    return HttpResponse.json(relationship);
  }),

  // === Locations API ===

  http.get(`${API_PREFIX}/locations`, async () => {
    await withLatency();
    return HttpResponse.json({
      locations: mockLocations,
      total: mockLocations.length,
    });
  }),

  http.get(`${API_PREFIX}/locations/:id`, async ({ params }) => {
    await withLatency();
    const location = mockLocations.find((l) => l.id === params.id);
    if (!location) {
      return HttpResponse.json({ detail: 'Location not found' }, { status: 404 });
    }
    return HttpResponse.json(location);
  }),

  http.get(`${API_PREFIX}/locations/:id/children`, async ({ params }) => {
    await withLatency();
    const parentId = params.id as string;
    const children = mockLocations.filter((l) => l.parent_location_id === parentId);
    return HttpResponse.json({
      locations: children,
      total: children.length,
    });
  }),

  // === Items API ===

  http.get(`${API_PREFIX}/items`, async ({ request }) => {
    await withLatency();
    const url = new URL(request.url);
    const itemType = url.searchParams.get('item_type');

    let filtered = mockItems;
    if (itemType) {
      filtered = mockItems.filter((item) => item.item_type === itemType);
    }

    return HttpResponse.json({
      items: filtered,
      total: filtered.length,
    });
  }),

  http.get(`${API_PREFIX}/items/:id`, async ({ params }) => {
    await withLatency();
    const item = mockItems.find((i) => i.id === params.id);
    if (!item) {
      return HttpResponse.json({ detail: 'Item not found' }, { status: 404 });
    }
    return HttpResponse.json(item);
  }),

  // === Character Inventory API ===

  http.get(`${API_PREFIX}/characters/:id/inventory`, async ({ params }) => {
    await withLatency();
    const characterId = params.id as string;
    const inventoryIds = characterInventories[characterId] || [];
    const items = mockItems.filter((item) => inventoryIds.includes(item.id));

    return HttpResponse.json({
      items,
      total: items.length,
    });
  }),

  http.post(`${API_PREFIX}/characters/:id/give-item`, async ({ params, request }) => {
    await withLatency();
    const characterId = params.id as string;
    const body = asObject(await request.json().catch(() => ({})));
    const itemId = stringField(body, 'item_id');

    const item = mockItems.find((i) => i.id === itemId);
    if (!item) {
      return HttpResponse.json({ detail: 'Item not found' }, { status: 404 });
    }

    if (!characterInventories[characterId]) {
      characterInventories[characterId] = [];
    }

    if (characterInventories[characterId].includes(itemId)) {
      return HttpResponse.json(
        { detail: `Item ${itemId} is already in character's inventory` },
        { status: 409 }
      );
    }

    characterInventories[characterId].push(itemId);

    return HttpResponse.json({
      success: true,
      message: `Item '${item.name}' added to character ${characterId}'s inventory`,
    });
  }),

  http.delete(`${API_PREFIX}/characters/:id/remove-item/:itemId`, async ({ params }) => {
    await withLatency();
    const characterId = params.id as string;
    const itemId = params.itemId as string;

    if (!characterInventories[characterId]) {
      return HttpResponse.json({
        success: false,
        message: `Character ${characterId} has no inventory`,
      });
    }

    const idx = characterInventories[characterId].indexOf(itemId);
    if (idx === -1) {
      return HttpResponse.json({
        success: false,
        message: `Item ${itemId} not in character's inventory`,
      });
    }

    characterInventories[characterId].splice(idx, 1);

    return HttpResponse.json({
      success: true,
      message: `Item ${itemId} removed from character ${characterId}'s inventory`,
    });
  }),
];
