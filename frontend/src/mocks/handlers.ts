import { http, HttpResponse, delay } from 'msw';
import type { CharacterDetail, CharacterSummary } from '@/shared/types/character';
import {
  CharactersListResponseSchema,
  OrchestrationStartRequestSchema,
  type RelationshipResponse,
  type WorldLocation,
  type ItemResponse,
  type LoreEntryResponse,
  type WorldRuleResponse,
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
    memories: [
      {
        memory_id: 'mem-001',
        content: 'The day I first saw the fractured realm from Meridian Station.',
        importance: 9,
        tags: ['origin', 'awakening'],
        timestamp: '2024-01-15T10:30:00Z',
        is_core_memory: true,
        importance_level: 'core',
      },
      {
        memory_id: 'mem-002',
        content: 'Meeting Aldric for the first time at the Trade Hub.',
        importance: 6,
        tags: ['relationship', 'ally'],
        timestamp: '2024-02-20T14:00:00Z',
        is_core_memory: false,
        importance_level: 'moderate',
      },
    ],
    goals: [
      {
        goal_id: 'goal-001',
        description: 'Unite the fractured territories under a single banner',
        status: 'ACTIVE',
        urgency: 'HIGH',
        created_at: '2024-01-20T08:00:00Z',
        completed_at: null,
        is_active: true,
        is_urgent: true,
      },
      {
        goal_id: 'goal-002',
        description: 'Discover the truth about the Sundering War',
        status: 'ACTIVE',
        urgency: 'MEDIUM',
        created_at: '2024-02-01T10:00:00Z',
        completed_at: null,
        is_active: true,
        is_urgent: false,
      },
      {
        goal_id: 'goal-003',
        description: 'Find a reliable source of information in each major city',
        status: 'COMPLETED',
        urgency: 'LOW',
        created_at: '2024-01-05T12:00:00Z',
        completed_at: '2024-02-15T16:30:00Z',
        is_active: false,
        is_urgent: false,
      },
      {
        goal_id: 'goal-004',
        description: 'Defeat Lord Vexar in open combat',
        status: 'ACTIVE',
        urgency: 'CRITICAL',
        created_at: '2024-03-01T09:00:00Z',
        completed_at: null,
        is_active: true,
        is_urgent: true,
      },
      {
        goal_id: 'goal-005',
        description: 'Negotiate peace with the Mountain Clans',
        status: 'FAILED',
        urgency: 'HIGH',
        created_at: '2024-01-10T14:00:00Z',
        completed_at: '2024-02-28T11:00:00Z',
        is_active: false,
        is_urgent: false,
      },
    ],
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
    memories: [],
    goals: [
      {
        goal_id: 'goal-101',
        description: 'Establish trade routes to all major cities',
        status: 'ACTIVE',
        urgency: 'MEDIUM',
        created_at: '2024-01-15T09:00:00Z',
        completed_at: null,
        is_active: true,
        is_urgent: false,
      },
      {
        goal_id: 'goal-102',
        description: 'Accumulate enough wealth to buy a seat on the Merchant Council',
        status: 'ACTIVE',
        urgency: 'LOW',
        created_at: '2024-01-01T08:00:00Z',
        completed_at: null,
        is_active: true,
        is_urgent: false,
      },
    ],
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
    trust: 80,
    romance: 0,
    interaction_history: [],
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
    trust: 5,
    romance: 0,
    interaction_history: [],
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
    trust: 25,
    romance: 0,
    interaction_history: [],
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
    trust: 95,
    romance: 0,
    interaction_history: [],
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
    trust: 70,
    romance: 0,
    interaction_history: [],
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

// Mock lore entries for Wiki Dashboard
const mockLoreEntries: LoreEntryResponse[] = [
  {
    id: 'lore-001',
    title: 'The Sundering War',
    content:
      'A devastating conflict that split the continent of Eldara into warring kingdoms. The war lasted for three centuries and forever changed the political landscape.',
    category: 'history',
    tags: ['war', 'eldara', 'ancient'],
    created_at: nowIso(),
    updated_at: nowIso(),
  },
  {
    id: 'lore-002',
    title: 'Elven Moonweaving',
    content:
      'The ancient art of channeling lunar energy into protective wards and healing magic. Only practiced by elven priests at the Temple of Moonlight.',
    category: 'magic',
    tags: ['elven', 'magic', 'healing'],
    created_at: nowIso(),
    updated_at: nowIso(),
  },
  {
    id: 'lore-003',
    title: 'Dwarven Forgecraft',
    content:
      'The secret techniques passed down through generations of dwarven smiths. Ironhold Fortress is home to the greatest masters of this craft.',
    category: 'technology',
    tags: ['dwarven', 'smithing', 'ironhold'],
    created_at: nowIso(),
    updated_at: nowIso(),
  },
  {
    id: 'lore-004',
    title: 'Festival of First Light',
    content:
      'An annual celebration marking the end of winter. Communities gather for feasts, dances, and the lighting of the Great Bonfire.',
    category: 'culture',
    tags: ['festival', 'tradition', 'celebration'],
    created_at: nowIso(),
    updated_at: nowIso(),
  },
  {
    id: 'lore-005',
    title: 'The Arcane Compact',
    content:
      'A treaty between mortal kingdoms and the fey courts, establishing boundaries and rules of engagement. Breaking this compact invites dire consequences.',
    category: 'history',
    tags: ['fey', 'treaty', 'law'],
    created_at: nowIso(),
    updated_at: nowIso(),
  },
];

// Mock world rules for the World Rules Editor
const mockWorldRules: WorldRuleResponse[] = [
  {
    id: 'rule-001',
    name: 'Magic requires stamina',
    description: 'All magical abilities draw from the caster\'s physical reserves. More powerful spells demand greater stamina expenditure.',
    consequence: 'Exhaustion and potential unconsciousness if stamina is depleted',
    exceptions: ['Divine magic from gods', 'Artifacts with stored energy'],
    category: 'magic',
    severity: 85,
    related_rule_ids: ['rule-002'],
    created_at: nowIso(),
    updated_at: nowIso(),
  },
  {
    id: 'rule-002',
    name: 'No teleportation within wards',
    description: 'Magical wards placed around settlements prevent all forms of instantaneous travel, including teleportation, dimension doors, and phase shifting.',
    consequence: 'Spell failure and magical backlash',
    exceptions: ['Ward keepers with authorization tokens', 'Emergency royal override'],
    category: 'magic',
    severity: 95,
    related_rule_ids: ['rule-001'],
    created_at: nowIso(),
    updated_at: nowIso(),
  },
  {
    id: 'rule-003',
    name: 'Iron repels the fey',
    description: 'Cold iron causes discomfort and weakening to fey creatures. Direct contact with pure iron causes burning damage.',
    consequence: 'Fey creatures suffer weakness and pain near iron',
    exceptions: ['Half-fey with mortal blood', 'Fey who have sworn iron-pacts'],
    category: 'physics',
    severity: 100,
    related_rule_ids: [],
    created_at: nowIso(),
    updated_at: nowIso(),
  },
];

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
      memories: [],
      goals: [],
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

  // === Lore API ===

  http.get(`${API_PREFIX}/lore`, async ({ request }) => {
    await withLatency();
    const url = new URL(request.url);
    const category = url.searchParams.get('category');

    let filtered = mockLoreEntries;
    if (category) {
      filtered = mockLoreEntries.filter((entry) => entry.category === category);
    }

    return HttpResponse.json({
      entries: filtered,
      total: filtered.length,
    });
  }),

  http.get(`${API_PREFIX}/lore/search`, async ({ request }) => {
    await withLatency();
    const url = new URL(request.url);
    const query = url.searchParams.get('q')?.toLowerCase() || '';
    const tags = url.searchParams.get('tags')?.split(',').filter(Boolean) || [];
    const category = url.searchParams.get('category');

    let filtered = mockLoreEntries;

    if (query) {
      filtered = filtered.filter(
        (entry) =>
          entry.title.toLowerCase().includes(query) ||
          entry.content.toLowerCase().includes(query)
      );
    }

    if (tags.length > 0) {
      filtered = filtered.filter((entry) => tags.some((tag) => entry.tags.includes(tag)));
    }

    if (category) {
      filtered = filtered.filter((entry) => entry.category === category);
    }

    return HttpResponse.json({
      entries: filtered,
      total: filtered.length,
    });
  }),

  http.get(`${API_PREFIX}/lore/:id`, async ({ params }) => {
    await withLatency();
    const entry = mockLoreEntries.find((e) => e.id === params.id);
    if (!entry) {
      return HttpResponse.json({ detail: 'Lore entry not found' }, { status: 404 });
    }
    return HttpResponse.json(entry);
  }),

  // === Generation API ===

  http.post(`${API_PREFIX}/generation/character-profile`, async ({ request }) => {
    // Simulate LLM processing delay
    await delay(1500);

    const body = asObject(await request.json().catch(() => ({})));
    const name = stringField(body, 'name', 'Unknown Character');
    const archetype = stringField(body, 'archetype', 'Hero');
    const context = stringField(body, 'context', '');

    // Mock profile generation based on archetype
    const archetypeKey = archetype.toLowerCase();
    const templates: Record<
      string,
      {
        aliases: string[];
        traits: string[];
        appearance: string;
        backstory: string;
        motivations: string[];
        quirks: string[];
      }
    > = {
      hero: {
        aliases: ['The Lightbringer', 'Champion of the Dawn'],
        traits: ['courageous', 'selfless', 'determined', 'honorable'],
        appearance:
          'Tall and well-built with confident posture. Eyes gleam with inner resolve. Wears practical armor with subtle heroic embellishments.',
        backstory:
          'Rose from humble origins after witnessing injustice firsthand. Trained under a renowned mentor before embarking on their quest.',
        motivations: ['protect the innocent', 'right past wrongs', 'find redemption'],
        quirks: ['always helps those in need', 'never breaks a promise'],
      },
      villain: {
        aliases: ['The Dark Tyrant', 'Lord of Shadows'],
        traits: ['ruthless', 'calculating', 'charismatic', 'ambitious'],
        appearance:
          'Imposing figure cloaked in darkness. Sharp features with piercing eyes that seem to see through deception.',
        backstory:
          'Once a respected figure, twisted by betrayal and loss. Now seeks to reshape the world according to their vision.',
        motivations: ['absolute power', 'revenge on betrayers', 'create order through fear'],
        quirks: ['speaks in measured tones', 'collects trophies from fallen foes'],
      },
      mentor: {
        aliases: ['The Sage', 'Keeper of Ancient Ways'],
        traits: ['wise', 'patient', 'cryptic', 'protective'],
        appearance:
          'Weathered features that speak of long experience. Gentle eyes that hold depths of knowledge.',
        backstory:
          'Has walked many paths and learned from countless trials. Now seeks to pass on wisdom to the next generation.',
        motivations: ['guide the worthy', 'preserve ancient knowledge', 'prevent past mistakes'],
        quirks: ['speaks in riddles', 'appears when least expected'],
      },
      rogue: {
        aliases: ['Shadow Dancer', 'The Ghost'],
        traits: ['cunning', 'charming', 'resourceful', 'independent'],
        appearance:
          'Lithe and agile with quick, graceful movements. Unremarkable features that blend into any crowd.',
        backstory:
          'Learned to survive on the streets from a young age. Trust is hard-earned, but loyalty once given is absolute.',
        motivations: ['freedom', 'wealth', 'protect street family'],
        quirks: ['fidgets with coins', 'always knows the exits'],
      },
    };

    const template = templates[archetypeKey] || {
      aliases: [`${name} the Unknown`, 'The Mysterious One'],
      traits: ['enigmatic', 'adaptable', 'observant'],
      appearance: 'Average build with nondescript features. Something about them defies easy categorization.',
      backstory: `Origins shrouded in mystery. ${context || 'Their past remains unknown.'}`,
      motivations: ['unknown goals', 'hidden agenda'],
      quirks: ['rarely speaks of the past'],
    };

    return HttpResponse.json({
      name,
      aliases: template.aliases,
      archetype,
      traits: template.traits,
      appearance: template.appearance,
      backstory: template.backstory,
      motivations: template.motivations,
      quirks: template.quirks,
    });
  }),

  // === World Rules API ===

  http.get(`${API_PREFIX}/world-rules`, async ({ request }) => {
    await withLatency();
    const url = new URL(request.url);
    const category = url.searchParams.get('category');
    const minSeverity = url.searchParams.get('min_severity');
    const maxSeverity = url.searchParams.get('max_severity');

    let filtered = mockWorldRules;

    if (category) {
      filtered = filtered.filter((rule) => rule.category === category);
    }

    if (minSeverity) {
      const min = parseInt(minSeverity, 10);
      filtered = filtered.filter((rule) => rule.severity >= min);
    }

    if (maxSeverity) {
      const max = parseInt(maxSeverity, 10);
      filtered = filtered.filter((rule) => rule.severity <= max);
    }

    return HttpResponse.json({
      rules: filtered,
      total: filtered.length,
    });
  }),

  http.get(`${API_PREFIX}/world-rules/search`, async ({ request }) => {
    await withLatency();
    const url = new URL(request.url);
    const query = url.searchParams.get('q')?.toLowerCase() || '';
    const category = url.searchParams.get('category');

    let filtered = mockWorldRules;

    if (query) {
      filtered = filtered.filter((rule) =>
        rule.name.toLowerCase().includes(query)
      );
    }

    if (category) {
      filtered = filtered.filter((rule) => rule.category === category);
    }

    return HttpResponse.json({
      rules: filtered,
      total: filtered.length,
    });
  }),

  http.get(`${API_PREFIX}/world-rules/absolute`, async () => {
    await withLatency();
    const absoluteRules = mockWorldRules.filter((rule) => rule.severity >= 90);
    return HttpResponse.json({
      rules: absoluteRules,
      total: absoluteRules.length,
    });
  }),

  http.get(`${API_PREFIX}/world-rules/:id`, async ({ params }) => {
    await withLatency();
    const rule = mockWorldRules.find((r) => r.id === params.id);
    if (!rule) {
      return HttpResponse.json({ detail: 'World rule not found' }, { status: 404 });
    }
    return HttpResponse.json(rule);
  }),

  http.post(`${API_PREFIX}/world-rules`, async ({ request }) => {
    await withLatency();
    const body = asObject(await request.json().catch(() => ({})));

    const name = stringField(body, 'name');
    if (!name) {
      return HttpResponse.json({ detail: 'Name is required' }, { status: 400 });
    }

    const newRule: WorldRuleResponse = {
      id: `rule-${Date.now()}`,
      name,
      description: stringField(body, 'description'),
      consequence: stringField(body, 'consequence'),
      exceptions: arrayField(body, 'exceptions', []),
      category: stringField(body, 'category'),
      severity: typeof body.severity === 'number' ? body.severity : 50,
      related_rule_ids: [],
      created_at: nowIso(),
      updated_at: nowIso(),
    };

    mockWorldRules.push(newRule);
    return HttpResponse.json(newRule, { status: 201 });
  }),

  http.put(`${API_PREFIX}/world-rules/:id`, async ({ params, request }) => {
    await withLatency();
    const ruleIndex = mockWorldRules.findIndex((r) => r.id === params.id);
    if (ruleIndex === -1) {
      return HttpResponse.json({ detail: 'World rule not found' }, { status: 404 });
    }

    const body = asObject(await request.json().catch(() => ({})));
    const existingRule = mockWorldRules[ruleIndex];
    if (!existingRule) {
      return HttpResponse.json({ detail: 'World rule not found' }, { status: 404 });
    }

    const updatedRule: WorldRuleResponse = {
      ...existingRule,
      name: 'name' in body ? stringField(body, 'name') : existingRule.name,
      description: 'description' in body ? stringField(body, 'description') : existingRule.description,
      consequence: 'consequence' in body ? stringField(body, 'consequence') : existingRule.consequence,
      exceptions: 'exceptions' in body ? arrayField(body, 'exceptions', []) : existingRule.exceptions,
      category: 'category' in body ? stringField(body, 'category') : existingRule.category,
      severity: 'severity' in body && typeof body.severity === 'number' ? body.severity : existingRule.severity,
      updated_at: nowIso(),
    };

    mockWorldRules[ruleIndex] = updatedRule;
    return HttpResponse.json(updatedRule);
  }),

  http.delete(`${API_PREFIX}/world-rules/:id`, async ({ params }) => {
    await withLatency();
    const ruleIndex = mockWorldRules.findIndex((r) => r.id === params.id);
    if (ruleIndex === -1) {
      return HttpResponse.json({ detail: 'World rule not found' }, { status: 404 });
    }

    mockWorldRules.splice(ruleIndex, 1);
    return new HttpResponse(null, { status: 204 });
  }),

  // === Dialogue Generation (CHAR-028) ===
  http.post(`${API_PREFIX}/dialogue/generate`, async ({ request }) => {
    await withLatency();
    const body = asObject(await request.json().catch(() => ({})));

    const characterId = stringField(body, 'character_id');
    const context = stringField(body, 'context');
    const mood = stringField(body, 'mood');

    if (!characterId || !context) {
      return HttpResponse.json(
        { detail: 'character_id and context are required' },
        { status: 400 }
      );
    }

    // Generate mock dialogue based on mood and context
    const dialogueResponses: Record<string, { dialogue: string; tone: string; thought: string; body: string }> = {
      angry: {
        dialogue: "Don't test my patience. I've dealt with far worse than this.",
        tone: 'threatening',
        thought: 'This is beneath me, but I must maintain composure.',
        body: 'clenches fist, jaw tightens',
      },
      happy: {
        dialogue: "What a wonderful surprise! This day just keeps getting better.",
        tone: 'enthusiastic',
        thought: "I should savor this moment - they're rare enough.",
        body: 'eyes brighten, slight smile appears',
      },
      sad: {
        dialogue: "I... I suppose that makes sense. Things rarely go the way we hope.",
        tone: 'melancholic',
        thought: 'Another disappointment. But I expected as much.',
        body: 'shoulders slump slightly, gaze drops',
      },
      fearful: {
        dialogue: "We should... we should proceed carefully. Something feels wrong.",
        tone: 'nervous',
        thought: 'Every instinct tells me to run.',
        body: 'eyes dart around, steps back slightly',
      },
      cautious: {
        dialogue: "I've seen deals like this before. What's the catch?",
        tone: 'suspicious',
        thought: "Nothing is ever this simple. There's always a price.",
        body: 'narrows eyes, crosses arms',
      },
      excited: {
        dialogue: "Finally! I've been waiting for something like this!",
        tone: 'eager',
        thought: 'This could change everything.',
        body: 'leans forward, eyes wide with anticipation',
      },
      default: {
        dialogue: "Interesting. Tell me more about what you have in mind.",
        tone: 'neutral',
        thought: "Let's see where this leads before committing.",
        body: 'maintains neutral expression, tilts head slightly',
      },
    };

    const responseKey = mood || 'default';
    const response = dialogueResponses[responseKey] ?? dialogueResponses['default'];

    return HttpResponse.json({
      dialogue: response?.dialogue ?? '...',
      tone: response?.tone ?? 'neutral',
      internal_thought: response?.thought ?? null,
      body_language: response?.body ?? null,
      character_id: characterId,
      error: null,
    });
  }),

  // === Social Network Analysis (CHAR-031/CHAR-032) ===
  http.get(`${API_PREFIX}/social/analysis`, async () => {
    await withLatency();

    // Compute social analysis from mock relationships (character-to-character only)
    const charRelationships = mockRelationships.filter(
      (r) => r.source_type === 'character' && r.target_type === 'character'
    );

    // Unique characters in relationships
    const characterIds = new Set<string>();
    charRelationships.forEach((r) => {
      characterIds.add(r.source_id);
      characterIds.add(r.target_id);
    });

    // Calculate centrality for each character
    interface CentralityMetrics {
      character_id: string;
      relationship_count: number;
      positive_count: number;
      negative_count: number;
      average_trust: number;
      average_romance: number;
      centrality_score: number;
    }

    const centralities: Record<string, CentralityMetrics> = {};
    const positiveTypes = ['ally', 'family', 'mentor', 'romantic'];
    const negativeTypes = ['enemy', 'rival'];

    characterIds.forEach((charId) => {
      const related = charRelationships.filter(
        (r) => r.source_id === charId || r.target_id === charId
      );

      const positiveCount = related.filter((r) =>
        positiveTypes.includes(r.relationship_type)
      ).length;
      const negativeCount = related.filter((r) =>
        negativeTypes.includes(r.relationship_type)
      ).length;

      const avgTrust =
        related.length > 0
          ? related.reduce((sum, r) => sum + r.trust, 0) / related.length
          : 0;
      const avgRomance =
        related.length > 0
          ? related.reduce((sum, r) => sum + r.romance, 0) / related.length
          : 0;

      centralities[charId] = {
        character_id: charId,
        relationship_count: related.length,
        positive_count: positiveCount,
        negative_count: negativeCount,
        average_trust: avgTrust,
        average_romance: avgRomance,
        centrality_score: 0, // computed after
      };
    });

    // Normalize centrality scores (highest relationship count = 100)
    const maxRelCount = Math.max(
      ...Object.values(centralities).map((c) => c.relationship_count),
      1
    );
    Object.values(centralities).forEach((c) => {
      c.centrality_score = (c.relationship_count / maxRelCount) * 100;
    });

    // Find most connected (highest relationship_count)
    const mostConnected = Object.values(centralities).reduce(
      (max, c) => (c.relationship_count > (max?.relationship_count ?? 0) ? c : max),
      null as CentralityMetrics | null
    );

    // Find most hated (most negative relationships)
    const mostHated = Object.values(centralities).reduce(
      (max, c) => (c.negative_count > (max?.negative_count ?? 0) ? c : max),
      null as CentralityMetrics | null
    );

    // Find most loved (highest weighted score: trust * 0.6 + romance * 0.4)
    const mostLoved = Object.values(centralities).reduce((max, c) => {
      const score = c.average_trust * 0.6 + c.average_romance * 0.4;
      const maxScore = max
        ? max.average_trust * 0.6 + max.average_romance * 0.4
        : 0;
      return score > maxScore ? c : max;
    }, null as CentralityMetrics | null);

    // Network density
    const totalChars = characterIds.size;
    const maxPossibleEdges = totalChars * (totalChars - 1);
    const density =
      maxPossibleEdges > 0
        ? Math.min(charRelationships.length / maxPossibleEdges, 1)
        : 0;

    return HttpResponse.json({
      character_centralities: centralities,
      most_connected: mostConnected?.character_id ?? null,
      most_hated: mostHated?.character_id ?? null,
      most_loved: mostLoved?.character_id ?? null,
      total_relationships: charRelationships.length,
      total_characters: totalChars,
      network_density: density,
    });
  }),

  http.get(`${API_PREFIX}/social/analysis/:characterId`, async ({ params }) => {
    await withLatency();

    const { characterId } = params;
    if (typeof characterId !== 'string') {
      return HttpResponse.json({ detail: 'Invalid character ID' }, { status: 400 });
    }

    // Get relationships for this character
    const charRelationships = mockRelationships.filter(
      (r) =>
        r.source_type === 'character' &&
        r.target_type === 'character' &&
        (r.source_id === characterId || r.target_id === characterId)
    );

    if (charRelationships.length === 0) {
      return HttpResponse.json(
        { detail: `No relationships found for character: ${characterId}` },
        { status: 404 }
      );
    }

    const positiveTypes = ['ally', 'family', 'mentor', 'romantic'];
    const negativeTypes = ['enemy', 'rival'];

    const positiveCount = charRelationships.filter((r) =>
      positiveTypes.includes(r.relationship_type)
    ).length;
    const negativeCount = charRelationships.filter((r) =>
      negativeTypes.includes(r.relationship_type)
    ).length;

    const avgTrust =
      charRelationships.reduce((sum, r) => sum + r.trust, 0) /
      charRelationships.length;
    const avgRomance =
      charRelationships.reduce((sum, r) => sum + r.romance, 0) /
      charRelationships.length;

    // Get max relationship count for normalization
    const allCharRelationships = mockRelationships.filter(
      (r) => r.source_type === 'character' && r.target_type === 'character'
    );
    const charIds = new Set<string>();
    allCharRelationships.forEach((r) => {
      charIds.add(r.source_id);
      charIds.add(r.target_id);
    });
    const maxRelCount = Math.max(
      ...Array.from(charIds).map(
        (id) =>
          allCharRelationships.filter(
            (r) => r.source_id === id || r.target_id === id
          ).length
      ),
      1
    );

    return HttpResponse.json({
      character_id: characterId,
      relationship_count: charRelationships.length,
      positive_count: positiveCount,
      negative_count: negativeCount,
      average_trust: avgTrust,
      average_romance: avgRomance,
      centrality_score: (charRelationships.length / maxRelCount) * 100,
    });
  }),
];
